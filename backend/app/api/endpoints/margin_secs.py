"""
融资融券标的 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

import asyncio
from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.margin_secs_service import MarginSecsService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_margin_secs(
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    exchange: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """获取融资融券标的数据（单日筛选 + 分页）"""
    service = MarginSecsService()
    result = await service.get_margin_secs_data(
        trade_date=trade_date,
        ts_code=ts_code,
        exchange=exchange,
        page=page,
        page_size=page_size
    )
    return ApiResponse.success(data=result)


@router.get("/latest")
@handle_api_errors
async def get_latest_margin_secs(exchange: Optional[str] = None):
    """获取最新交易日的融资融券标的数据"""
    service = MarginSecsService()
    result = await service.get_latest_data(exchange=exchange)
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_margin_secs_statistics(
    trade_date: Optional[str] = None,
    exchange: Optional[str] = None
):
    """获取融资融券标的统计信息"""
    from app.repositories import MarginSecsRepository

    repo = MarginSecsRepository()
    trade_date_fmt = trade_date.replace('-', '') if trade_date else None

    statistics = await asyncio.to_thread(
        repo.get_statistics,
        start_date=trade_date_fmt,
        end_date=trade_date_fmt,
        exchange=exchange
    )

    return ApiResponse.success(data=statistics)


@router.post("/sync-async")
@handle_api_errors
async def sync_margin_secs_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步融资融券标的数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.repositories.sync_config_repository import SyncConfigRepository

    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'margin_secs')
    task_name = (cfg.get('incremental_task_name') or 'extended.sync_margin_secs') if cfg else 'extended.sync_margin_secs'

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(task_name)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name='融资融券标的增量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='margin_secs_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="增量同步任务已提交，正在后台执行"
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_margin_secs_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步融资融券标的历史数据（按月切片，支持 Redis 续继）"""
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'margin_secs')
    from app.repositories.sync_config_repository import SyncConfigRepository

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'margin_secs')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(
        'tasks.sync_margin_secs_full_history',
        kwargs={'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_margin_secs_full_history',
        display_name='融资融券标的全量历史同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'concurrency': concurrency},
        source='margin_secs_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
