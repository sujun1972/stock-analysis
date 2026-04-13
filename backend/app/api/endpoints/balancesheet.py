"""
资产负债表数据API端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

import asyncio
from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.balancesheet_service import BalancesheetService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_balancesheet_data(
    start_date: Optional[str] = Query(None, description="开始日期（公告日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（公告日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    report_type: Optional[str] = Query(None, description="报告类型（1-12）"),
    limit: int = Query(30, ge=1, le=1000, description="限制返回记录数"),
    offset: int = Query(0, ge=0, description="分页偏移量")
):
    """查询资产负债表数据"""
    service = BalancesheetService()
    result = await service.get_balancesheet_data(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        period=period,
        report_type=report_type,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（公告日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（公告日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取资产负债表统计信息"""
    service = BalancesheetService()
    result = await service.get_statistics(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code
    )
    return ApiResponse.success(data=result)


@router.get("/latest")
@handle_api_errors
async def get_latest_balancesheet(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取最新资产负债表数据"""
    service = BalancesheetService()
    result = await service.get_latest_data(ts_code=ts_code)
    if result:
        return ApiResponse.success(data=result)
    else:
        return ApiResponse.success(data=None, message="暂无数据")


@router.post("/sync-async")
@handle_api_errors
async def sync_balancesheet_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步资产负债表数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.repositories.sync_config_repository import SyncConfigRepository

    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'balancesheet')
    task_name = (cfg.get('incremental_task_name') or 'tasks.sync_balancesheet') if cfg else 'tasks.sync_balancesheet'

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(task_name)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name='资产负债表增量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='balancesheet_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="增量同步任务已提交，正在后台执行"
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_balancesheet_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    触发全量历史资产负债表同步（可中断续继）

    逐只同步全部上市股票的资产负债表数据。
    中断后再次触发会自动从断点继续，跳过已同步完成的股票。
    """
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'balancesheet')
    from app.repositories.sync_config_repository import SyncConfigRepository

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'balancesheet')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(
        'tasks.sync_balancesheet_full_history',
        kwargs={'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_balancesheet_full_history',
        display_name='资产负债表全量历史同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'concurrency': concurrency},
        source='balancesheet_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
