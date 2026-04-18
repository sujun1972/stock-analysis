"""
利润表数据API端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.income_service import IncomeService
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_income_data(
    start_date: Optional[str] = Query(None, description="开始日期（报告期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（报告期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_type: Optional[str] = Query(None, description="报告类型（1-12）"),
    comp_type: Optional[str] = Query(None, description="公司类型（1-4）"),
    limit: int = Query(30, ge=1, le=1000, description="限制返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量（分页）")
):
    """查询利润表数据"""
    service = IncomeService()
    result = await service.get_income_data(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        report_type=report_type,
        comp_type=comp_type,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（报告期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（报告期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_type: Optional[str] = Query(None, description="报告类型")
):
    """获取利润表统计信息"""
    service = IncomeService()
    result = await service.get_statistics(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        report_type=report_type
    )
    return ApiResponse.success(data=result)


@router.get("/latest")
@handle_api_errors
async def get_latest_income(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取最新利润表数据"""
    service = IncomeService()
    result = await service.get_latest_data(ts_code=ts_code)
    if result:
        return ApiResponse.success(data=result)
    else:
        return ApiResponse.success(data=None, message="暂无数据")


@router.post("/sync-async")
@handle_api_errors
async def sync_income_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步利润表数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='income',
        display_name='利润表增量同步',
        fallback_task_name='tasks.sync_income',
        user_id=current_user.id,
        source='income_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_income_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史利润表同步（可中断续继）"""
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='income',
        display_name='利润表全量历史同步',
        task_name='tasks.sync_income_full_history',
        user_id=current_user.id,
        source='income_page',
        concurrency=concurrency,
        default_concurrency=5,
    )
