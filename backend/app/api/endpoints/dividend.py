"""
分红送股数据 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.api.error_handler import handle_api_errors
from app.services.dividend_service import DividendService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_dividend(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量（用于分页）")
):
    """查询分红送股数据"""
    service = DividendService()
    result = await service.get_dividend_data(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_dividend_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取分红送股统计信息"""
    service = DividendService()

    # 日期格式转换
    start_date_fmt = start_date.replace('-', '') if start_date else None
    end_date_fmt = end_date.replace('-', '') if end_date else None

    statistics = await asyncio.to_thread(
        service.dividend_repo.get_statistics,
        start_date=start_date_fmt,
        end_date=end_date_fmt,
        ts_code=ts_code
    )

    return ApiResponse.success(data=statistics)


@router.post("/sync-async")
@handle_api_errors
async def sync_dividend_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步分红送股数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.repositories.sync_config_repository import SyncConfigRepository

    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'dividend')
    task_name = (cfg.get('incremental_task_name') or 'tasks.sync_dividend') if cfg else 'tasks.sync_dividend'

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(task_name)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name='分红送股增量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='dividend_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="增量同步任务已提交，正在后台执行"
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_dividend_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史分红送股同步（可中断续继）"""
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'dividend')
    from app.repositories.sync_config_repository import SyncConfigRepository

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'dividend')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(
        'tasks.sync_dividend_full_history',
        kwargs={'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_dividend_full_history',
        display_name='分红送股全量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'concurrency': concurrency},
        source='dividend_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
