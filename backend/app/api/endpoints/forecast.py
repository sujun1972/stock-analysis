"""
业绩预告数据API端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.forecast_service import ForecastService
from app.core.dependencies import require_admin
from app.models.user import User


router = APIRouter()


@router.get("")
@handle_api_errors
async def get_forecast(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    type: Optional[str] = Query(None, description="预告类型，如：预增、预减、扭亏、首亏"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制"),
    offset: int = Query(0, ge=0, description="分页偏移量")
):
    """查询业绩预告数据"""
    service = ForecastService()
    result = await service.get_forecast_data(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        period=period,
        type_=type,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    type: Optional[str] = Query(None, description="预告类型，如：预增、预减、扭亏、首亏")
):
    """获取业绩预告统计信息"""
    service = ForecastService()
    statistics = await service.get_statistics(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        type_=type
    )
    return ApiResponse.success(data=statistics)


@router.get("/latest")
@handle_api_errors
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH")
):
    """获取最新业绩预告数据"""
    service = ForecastService()
    latest = await service.get_latest_data(ts_code=ts_code)
    return ApiResponse.success(data=latest)


@router.post("/sync-async")
@handle_api_errors
async def sync_forecast_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步业绩预告数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='forecast',
        display_name='业绩预告增量同步',
        fallback_task_name='tasks.sync_forecast',
        user_id=current_user.id,
        source='forecast_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_forecast_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史业绩预告同步（可中断续继）"""
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='forecast',
        display_name='业绩预告全量同步',
        task_name='tasks.sync_forecast_full_history',
        user_id=current_user.id,
        source='forecast_page',
        concurrency=concurrency,
        default_concurrency=5,
    )
