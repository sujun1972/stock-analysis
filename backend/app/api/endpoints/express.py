"""
业绩快报数据 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.express_service import ExpressService

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_express(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="限制返回数量"),
    offset: int = Query(0, ge=0, description="分页偏移量")
):
    """查询业绩快报数据"""
    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
    start_date_fmt = start_date.replace('-', '') if start_date else None
    end_date_fmt = end_date.replace('-', '') if end_date else None
    period_fmt = period.replace('-', '') if period else None

    service = ExpressService()
    result = await service.get_express_data(
        ts_code=ts_code,
        start_date=start_date_fmt,
        end_date=end_date_fmt,
        period=period_fmt,
        limit=limit,
        offset=offset
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取业绩快报统计信息"""
    # 转换日期格式
    start_date_fmt = start_date.replace('-', '') if start_date else None
    end_date_fmt = end_date.replace('-', '') if end_date else None

    service = ExpressService()
    stats = await service.get_statistics(
        start_date=start_date_fmt,
        end_date=end_date_fmt,
        ts_code=ts_code
    )

    return ApiResponse.success(data=stats)


@router.post("/sync-async")
@handle_api_errors
async def sync_express_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步业绩快报数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='express',
        display_name='业绩快报增量同步',
        fallback_task_name='tasks.sync_express',
        user_id=current_user.id,
        source='express_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_express_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史业绩快报同步（可中断续继）"""
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='express',
        display_name='业绩快报全量同步',
        task_name='tasks.sync_express_full_history',
        user_id=current_user.id,
        source='express_page',
        concurrency=concurrency,
        default_concurrency=5,
    )
