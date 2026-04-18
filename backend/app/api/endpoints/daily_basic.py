"""
每日指标数据API端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history，委托 TushareSyncBase
"""

import asyncio
from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.api.error_handler import handle_api_errors
from app.core.dependencies import get_current_user, require_admin
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.daily_basic_service import DailyBasicService

router = APIRouter(tags=["daily_basic"])


@router.get("")
@handle_api_errors
async def get_daily_basic_list(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量")
):
    """查询每日指标数据"""
    service = DailyBasicService()

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    result = await service.get_daily_basic_list(
        trade_date=trade_date_formatted,
        ts_code=ts_code,
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        page=page,
        page_size=page_size
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_daily_basic_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取每日指标统计信息"""
    service = DailyBasicService()

    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    stats = await service.get_statistics(
        start_date=start_date_formatted,
        end_date=end_date_formatted
    )

    return ApiResponse.success(data=stats)


@router.get("/latest")
@handle_api_errors
async def get_latest_daily_basic():
    """获取最新交易日的每日指标数据"""
    service = DailyBasicService()
    result = await service.get_latest_data()
    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_daily_basic_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步每日指标数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 get_suggested_start_date() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='daily_basic',
        display_name='每日指标增量同步',
        fallback_task_name='tasks.sync_daily_basic_incremental',
        user_id=current_user.id,
        source='daily_basic_page',
    )


@router.get("/full-history-progress")
@handle_api_errors
async def get_full_history_progress(
    current_user: User = Depends(get_current_user)
):
    """查询全量历史同步进度"""
    from app.core.redis_lock import redis_client
    from app.repositories.stock_basic_repository import StockBasicRepository

    completed = 0
    total = 0
    is_in_progress = False

    if redis_client:
        completed = redis_client.scard(DailyBasicService.FULL_HISTORY_PROGRESS_KEY) or 0
        is_in_progress = bool(redis_client.exists(DailyBasicService.FULL_HISTORY_LOCK_KEY))

    repo = StockBasicRepository()
    total = await asyncio.to_thread(repo.count_by_status, 'L')

    return ApiResponse.success(data={
        "completed": completed,
        "total": total,
        "is_in_progress": is_in_progress,
        "percent": round(completed / total * 100, 1) if total > 0 else 0
    })


@router.post("/sync-full-history")
@handle_api_errors
async def sync_daily_basic_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    触发全量历史每日指标同步（可中断续继）

    从2021年1月1日起，逐只同步全部上市股票的每日指标数据。
    中断后再次触发会自动从断点继续，跳过已同步完成的股票。
    """
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='daily_basic',
        display_name='每日指标全量历史同步',
        task_name='tasks.sync_daily_basic_full_history',
        user_id=current_user.id,
        source='daily_basic_page',
        concurrency=concurrency,
        default_concurrency=8,
    )
