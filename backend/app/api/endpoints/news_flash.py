"""财经快讯 API 端点（前缀 /news-flash）。

查询类：分页列表 / 源枚举 / 单股关联快讯。
同步类：增量（财新） / 全量（无历史，退化为增量） / 被动单股（东财个股新闻）。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

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
async def list_flash(
    source: Optional[str] = Query(None, description="来源：caixin / eastmoney"),
    start_time: Optional[str] = Query(None, description="起始时间 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS"),
    end_time: Optional[str] = Query(None, description="结束时间"),
    ts_code: Optional[str] = Query(None, description="关联的股票代码（精确匹配）"),
    keyword: Optional[str] = Query(None, description="标题/摘要关键字"),
    tag: Optional[str] = Query(None, description="tag 标签精确匹配"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None, description="排序字段：publish_time / source / created_at"),
    sort_order: str = Query('desc'),
):
    """分页查询财经快讯。"""
    from app.services.news_anns import NewsFlashSyncService
    svc = NewsFlashSyncService()
    result = await svc.list_flash(
        source=source, start_time=start_time, end_time=end_time,
        ts_code=ts_code, keyword=keyword, tag=tag,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return ApiResponse.success(data=result)


@router.get("/stock/{ts_code}")
@handle_api_errors
async def get_by_stock(
    ts_code: str,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
):
    """单只股票近 N 天关联的快讯（GIN 索引反查）。"""
    from app.services.news_anns import NewsFlashSyncService
    svc = NewsFlashSyncService()
    items = await svc.get_recent_by_stock(ts_code, days=days, limit=limit)
    return ApiResponse.success(data={
        'ts_code': ts_code,
        'days': days,
        'items': items,
        'total': len(items),
    })


# ------------------------------------------------------------------
# 同步
# ------------------------------------------------------------------

@router.post("/sync-async")
@handle_api_errors
async def sync_async(current_user: User = Depends(require_admin)):
    """增量同步财新要闻精选（拉最近 ~100 条）。"""
    return await dispatch_incremental_sync(
        table_key='news_flash',
        display_name='财经快讯增量同步',
        fallback_task_name='tasks.sync_news_flash',
        user_id=current_user.id,
        source='news_flash_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=5),
    current_user: User = Depends(require_admin),
):
    """全量同步（注：AkShare 快讯接口无历史参数，退化为一次增量抓取）。"""
    return await dispatch_full_history_sync(
        table_key='news_flash',
        display_name='财经快讯全量同步',
        task_name='tasks.sync_news_flash_full_history',
        user_id=current_user.id,
        source='news_flash_page',
        concurrency=concurrency,
        default_concurrency=1,
    )


@router.post("/sync/{ts_code}")
@handle_api_errors
async def sync_by_stock(
    ts_code: str,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_admin),
):
    """单只股票被动同步（前端 AI 分析弹窗打开前触发）。"""
    from app.celery_app import celery_app
    task = celery_app.send_task(
        'tasks.sync_news_flash_single',
        kwargs={'ts_code': ts_code, 'days': int(days)},
    )
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=task.id,
        task_name='tasks.sync_news_flash_single',
        display_name=f'个股新闻被动同步 {ts_code}',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'ts_code': ts_code, 'days': int(days)},
        source='news_flash_page',
    )
    return ApiResponse.success(
        data=task_data,
        message=f"已提交 {ts_code} 被动同步任务",
    )
