"""公司公告 API 端点（前缀 /stock-anns）。

查询类端点：分页列表 / 公告类型枚举 / 单股查询 / 正文查询。
同步类端点：增量 / 全量历史 / 被动单股 / 正文按需抓取。
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.error_handler import handle_api_errors
from app.api.sync_utils import dispatch_full_history_sync, dispatch_incremental_sync
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services import TaskHistoryHelper

router = APIRouter()


# ------------------------------------------------------------------
# 查询
# ------------------------------------------------------------------

@router.get("")
@handle_api_errors
async def list_announcements(
    ts_code: Optional[str] = Query(None, description="股票代码（可选）"),
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    anno_type: Optional[str] = Query(None, description="公告类型筛选"),
    keyword: Optional[str] = Query(None, description="标题关键字（模糊匹配）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None, description="排序字段：ann_date / ts_code / anno_type / created_at"),
    sort_order: str = Query('desc', description="asc / desc"),
):
    """分页查询公司公告列表（admin 浏览页用）。"""
    from app.services.news_anns import StockAnnsSyncService
    svc = StockAnnsSyncService()
    start_fmt = start_date.strftime('%Y-%m-%d') if start_date else None
    end_fmt = end_date.strftime('%Y-%m-%d') if end_date else None
    result = await svc.list_anns(
        ts_code=ts_code, start_date=start_fmt, end_date=end_fmt,
        anno_type=anno_type, keyword=keyword,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return ApiResponse.success(data=result)


@router.get("/anno-types")
@handle_api_errors
async def list_anno_types(
    days: int = Query(90, ge=1, le=3650, description="回看天数（影响下拉可选项）"),
    limit: int = Query(200, ge=1, le=500),
):
    """返回近 N 天出现过的公告类型 + 计数（前端筛选下拉框）。"""
    import asyncio
    from app.repositories.stock_anns_repository import StockAnnsRepository
    repo = StockAnnsRepository()
    types = await asyncio.to_thread(repo.get_distinct_anno_types, days, limit)
    return ApiResponse.success(data={'items': types, 'days': days})


@router.get("/stock/{ts_code}")
@handle_api_errors
async def get_by_stock(
    ts_code: str,
    days: int = Query(30, ge=1, le=3650),
    limit: int = Query(50, ge=1, le=200),
):
    """单只股票近 N 天的公告（个股 AI 分析弹窗 + CIO 工具的底层数据源）。"""
    from app.services.news_anns import StockAnnsSyncService
    svc = StockAnnsSyncService()
    items = await svc.get_recent_by_stock(ts_code, days=days, limit=limit)
    return ApiResponse.success(data={
        'ts_code': ts_code,
        'days': days,
        'items': items,
        'total': len(items),
    })


@router.get("/content")
@handle_api_errors
async def get_content(
    ts_code: str = Query(..., description="股票代码"),
    ann_date: str = Query(..., description="公告日期 YYYY-MM-DD"),
    title: str = Query(..., description="公告标题"),
):
    """读取已抓取的公告正文（若未抓取则返回 null）。"""
    import asyncio
    from app.repositories.stock_anns_repository import StockAnnsRepository
    repo = StockAnnsRepository()
    record = await asyncio.to_thread(repo.get_content, ts_code, ann_date, title)
    if not record:
        return ApiResponse.not_found(message=f"未找到公告: {ts_code} / {ann_date} / {title}")
    return ApiResponse.success(data=record)


# ------------------------------------------------------------------
# 同步（增量 / 全量 / 被动单只 / 正文抓取）
# ------------------------------------------------------------------

@router.post("/sync-async")
@handle_api_errors
async def sync_async(current_user: User = Depends(require_admin)):
    """增量同步公司公告（按 sync_configs.incremental_default_days 回看窗口）。"""
    return await dispatch_incremental_sync(
        table_key='stock_anns',
        display_name='公司公告增量同步',
        fallback_task_name='tasks.sync_stock_anns',
        user_id=current_user.id,
        source='stock_anns_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=20),
    start_date: Optional[date] = Query(None, description="起始日期（覆盖默认 20200101，可缩短全量窗口）"),
    current_user: User = Depends(require_admin),
):
    """全量历史同步（按交易日切片 + Redis Set 续继）。"""
    extra = {}
    if start_date:
        extra['start_date'] = start_date.strftime('%Y%m%d')
    return await dispatch_full_history_sync(
        table_key='stock_anns',
        display_name='公司公告全量历史同步',
        task_name='tasks.sync_stock_anns_full_history',
        user_id=current_user.id,
        source='stock_anns_page',
        concurrency=concurrency,
        default_concurrency=5,
        extra_task_params=extra or None,
    )


@router.post("/sync/{ts_code}")
@handle_api_errors
async def sync_by_stock(
    ts_code: str,
    days: int = Query(90, ge=1, le=3650),
    current_user: User = Depends(require_admin),
):
    """单只股票被动同步（前端 AI 分析弹窗打开前调一次，拉近 `days` 天公告）。"""
    from app.celery_app import celery_app
    task = celery_app.send_task(
        'tasks.sync_stock_anns_single',
        kwargs={'ts_code': ts_code, 'days': int(days)},
    )
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=task.id,
        task_name='tasks.sync_stock_anns_single',
        display_name=f'公司公告被动同步 {ts_code}',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'ts_code': ts_code, 'days': int(days)},
        source='stock_anns_page',
    )
    return ApiResponse.success(
        data=task_data,
        message=f"已提交 {ts_code} 被动同步任务",
    )


class FetchContentEntry(BaseModel):
    """单条待抓取公告（ts_code/ann_date/title 用于 write-back，可选）。"""
    url: str
    ts_code: Optional[str] = None
    ann_date: Optional[str] = None
    title: Optional[str] = None


class FetchContentBody(BaseModel):
    entries: List[FetchContentEntry] = Field(default_factory=list)
    write_back: bool = Field(default=True, description="抓取成功后是否写回 stock_anns.content")


@router.post("/fetch-content")
@handle_api_errors
async def fetch_content(
    body: FetchContentBody,
    current_user: User = Depends(require_admin),
):
    """按需抓取公告正文（单次最多 5 个 URL，间隔 2 秒）。"""
    from app.services.news_anns.anns_content_fetcher import AnnsContentFetcher
    fetcher = AnnsContentFetcher()
    entries = [e.model_dump(exclude_none=False) for e in body.entries]
    results = await fetcher.fetch_batch(entries, write_back=body.write_back)
    ok = sum(1 for r in results if r.get('ok'))
    return ApiResponse.success(data={
        'requested': len(body.entries),
        'processed': len(results),
        'succeeded': ok,
        'results': results,
    })
