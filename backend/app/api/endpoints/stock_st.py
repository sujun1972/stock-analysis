"""
ST股票信息 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history，支持 Redis 续继
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.stock_st_service import StockStService
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_stock_st_data(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    st_type: Optional[str] = Query(None, description="ST类型：S-ST，*S-*ST，R-解除ST"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(30, ge=1, le=100, description="每页记录数，最大100")
):
    """查询ST股票数据（支持分页）"""
    service = StockStService()

    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    result = await service.get_stock_st_data(
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        ts_code=ts_code,
        st_type=st_type,
        page=page,
        page_size=page_size
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取ST股票统计信息"""
    service = StockStService()

    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    stats = await service.get_statistics(
        start_date=start_date_formatted,
        end_date=end_date_formatted
    )

    return ApiResponse.success(data=stats)


@router.get("/latest")
@handle_api_errors
async def get_latest():
    """获取最新的交易日期"""
    service = StockStService()
    latest = await service.get_latest_data()
    return ApiResponse.success(data=latest)


@router.post("/sync-async")
@handle_api_errors
async def sync_stock_st_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步ST股票数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 get_suggested_start_date() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='stock_st',
        display_name='ST股票列表增量同步',
        fallback_task_name='tasks.sync_stock_st_incremental',
        user_id=current_user.id,
        source='stock_st_page',
    )


@router.get("/full-history-progress")
@handle_api_errors
async def get_full_history_progress(
    current_user: User = Depends(get_current_user)
):
    """查询全量历史同步进度"""
    from app.core.redis_lock import redis_client

    completed = 0
    is_in_progress = False

    if redis_client:
        completed = redis_client.scard(StockStService.FULL_HISTORY_PROGRESS_KEY) or 0
        is_in_progress = bool(redis_client.exists(StockStService.FULL_HISTORY_LOCK_KEY))

    return ApiResponse.success(data={
        "completed": completed,
        "is_in_progress": is_in_progress,
    })


@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    触发全量历史ST股票同步（可中断续继）

    从2016年1月1日起，按月切片同步全部ST股票数据。
    中断后再次触发会自动从断点继续，跳过已同步完成的月份。
    """
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='stock_st',
        display_name='ST股票列表全量历史同步',
        task_name='tasks.sync_stock_st_full_history',
        user_id=current_user.id,
        source='stock_st_page',
        concurrency=concurrency,
        default_concurrency=1,
        extra_task_params={'start_date': '20160101', 'scope': 'all'},
    )
