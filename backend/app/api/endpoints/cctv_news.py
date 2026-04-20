"""新闻联播 API 端点（前缀 /cctv-news）。

查询类：分页列表 / 按日查看。
同步类：增量（逐日回看 N 天） / 全量历史（按日并发 + Redis Set 续继） / 指定单日。
"""

from __future__ import annotations

from datetime import date
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
async def list_news(
    start_date: Optional[date] = Query(None, description="起始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    keyword: Optional[str] = Query(None, description="标题/全文关键字"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None, description="排序字段：news_date / seq_no / created_at"),
    sort_order: str = Query('desc'),
):
    """分页查询新闻联播文字稿。"""
    from app.services.news_anns import CctvNewsSyncService
    svc = CctvNewsSyncService()
    start_fmt = start_date.strftime('%Y-%m-%d') if start_date else None
    end_fmt = end_date.strftime('%Y-%m-%d') if end_date else None
    result = await svc.list_news(
        start_date=start_fmt, end_date=end_fmt,
        keyword=keyword,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return ApiResponse.success(data=result)


@router.get("/by-date/{news_date}")
@handle_api_errors
async def get_by_date(news_date: str, limit: int = Query(50, ge=1, le=100)):
    """查询某日的联播（按 seq_no 升序）。"""
    import asyncio
    from app.repositories.cctv_news_repository import CctvNewsRepository
    repo = CctvNewsRepository()
    items = await asyncio.to_thread(repo.query_by_date, news_date, limit)
    return ApiResponse.success(data={
        'news_date': news_date,
        'items': items,
        'total': len(items),
    })


# ------------------------------------------------------------------
# 同步
# ------------------------------------------------------------------

@router.post("/sync-async")
@handle_api_errors
async def sync_async(current_user: User = Depends(require_admin)):
    """增量同步新闻联播（按 sync_configs.incremental_default_days 回看）。"""
    return await dispatch_incremental_sync(
        table_key='cctv_news',
        display_name='新闻联播增量同步',
        fallback_task_name='tasks.sync_cctv_news',
        user_id=current_user.id,
        source='cctv_news_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=5),
    start_date: Optional[date] = Query(None, description="起始日期（覆盖默认 20200101）"),
    current_user: User = Depends(require_admin),
):
    """全量历史同步（按日并发 + Redis Set 续继）。"""
    extra = {}
    if start_date:
        extra['start_date'] = start_date.strftime('%Y%m%d')
    return await dispatch_full_history_sync(
        table_key='cctv_news',
        display_name='新闻联播全量历史同步',
        task_name='tasks.sync_cctv_news_full_history',
        user_id=current_user.id,
        source='cctv_news_page',
        concurrency=concurrency,
        default_concurrency=1,
        extra_task_params=extra or None,
    )
