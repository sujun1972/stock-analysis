"""
同步端点公共函数

消除 sync-async / sync-full-history 端点中的重复样板代码。
各端点只需调用 dispatch_incremental_sync() / dispatch_full_history_sync()，
传入表级参数即可。
"""

import asyncio
from typing import Dict, Optional

from loguru import logger

from app.models.api_response import ApiResponse
from app.services import TaskHistoryHelper


async def dispatch_incremental_sync(
    *,
    table_key: str,
    display_name: str,
    fallback_task_name: str,
    user_id: int,
    source: str,
    task_params: Optional[Dict] = None,
) -> ApiResponse:
    """
    标准增量同步分发：读取 sync_configs → 提交 Celery 任务 → 记录任务历史。

    Args:
        table_key: sync_configs 表的 table_key
        display_name: 任务显示名称（如 '每日指标增量同步'）
        fallback_task_name: sync_configs 未配置时的兜底任务名
        user_id: 当前用户 ID
        source: 触发来源（如 'daily_basic_page'）
        task_params: 传给 Celery 任务的额外参数（默认 {}）
    """
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.celery_app import celery_app

    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, table_key)
    task_name = (cfg.get('incremental_task_name') or fallback_task_name) if cfg else fallback_task_name

    if task_params:
        celery_task = celery_app.send_task(task_name, kwargs=task_params)
    else:
        celery_task = celery_app.send_task(task_name)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name=display_name,
        task_type='data_sync',
        user_id=user_id,
        task_params=task_params or {},
        source=source,
    )

    logger.info(f"{display_name}任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="增量同步任务已提交，正在后台执行",
    )


async def dispatch_full_history_sync(
    *,
    table_key: str,
    display_name: str,
    task_name: str,
    user_id: int,
    source: str,
    concurrency: Optional[int] = None,
    default_concurrency: int = 5,
    extra_task_params: Optional[Dict] = None,
) -> ApiResponse:
    """
    标准全量同步分发：释放残留锁 → 读取并发数 → 提交 Celery 任务 → 记录任务历史。

    Args:
        table_key: sync_configs 表的 table_key
        display_name: 任务显示名称（如 '每日指标全量历史同步'）
        task_name: Celery 全量任务名
        user_id: 当前用户 ID
        source: 触发来源
        concurrency: 前端传入的并发数（None 时从 sync_configs 读取）
        default_concurrency: sync_configs 未配置时的兜底并发数
        extra_task_params: 额外参数（如 start_date）
    """
    from app.api.endpoints.sync_dashboard import release_stale_lock
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.celery_app import celery_app

    await asyncio.to_thread(release_stale_lock, table_key)

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, table_key)
        concurrency = (cfg.get('full_sync_concurrency') or default_concurrency) if cfg else default_concurrency

    task_kwargs = {'concurrency': concurrency}
    if extra_task_params:
        task_kwargs.update(extra_task_params)

    celery_task = celery_app.send_task(task_name, kwargs=task_kwargs)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name=display_name,
        task_type='data_sync',
        user_id=user_id,
        task_params=task_kwargs,
        source=source,
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
