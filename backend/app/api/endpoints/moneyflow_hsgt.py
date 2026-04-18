"""
沪深港通资金流向API

提供沪股通、深股通、港股通(上海)、港股通(深圳)的资金流向数据接口，
支持查询历史数据、同步最新数据、获取最新资金流向等功能。
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.moneyflow_hsgt_service import MoneyflowHsgtService

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_moneyflow_hsgt(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=365, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取沪深港通资金流向数据

    Returns:
        包含资金流向数据的响应
    """
    service = MoneyflowHsgtService()
    result = await asyncio.to_thread(
        service.get_moneyflow_data,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )

    return ApiResponse.success(
        data=result,
        message="获取沪深港通资金流向成功"
    )

@router.post("/sync")
@handle_api_errors
async def sync_moneyflow_hsgt(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    同步沪深港通资金流向数据（管理员功能）
    """
    from app.services.extended_sync_service import ExtendedDataSyncService

    service = ExtendedDataSyncService()

    # 转换日期格式
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 执行同步
    result = await service.sync_moneyflow_hsgt(
        trade_date=trade_date_formatted,
        start_date=start_date_formatted,
        end_date=end_date_formatted
    )

    if result["status"] == "success":
        return ApiResponse.success(
            data=result,
            message=f"成功同步 {result['records']} 条资金流向数据"
        )
    else:
        return ApiResponse.error(
            message=result.get("error", "同步失败")
        )

@router.post("/sync-async")
@handle_api_errors
async def sync_moneyflow_hsgt_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步沪深港通资金流向数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.moneyflow_hsgt_tasks import sync_moneyflow_hsgt_task
    from app.services import TaskHistoryHelper

    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 提交Celery任务（异步执行）
    celery_task = sync_moneyflow_hsgt_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_moneyflow_hsgt',
        display_name='沪深港通资金流向',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        },
        source='moneyflow_hsgt_page'
    )

    logger.info(f"沪深港通资金流向同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_moneyflow_hsgt_full_history_async(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD，默认 2014-01-01"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量同步沪深港通资金流向历史数据（按自然月切片，支持中断续继）
    """
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'moneyflow_hsgt')
    from app.tasks.moneyflow_hsgt_tasks import sync_moneyflow_hsgt_full_history_task
    from app.services import TaskHistoryHelper
    from app.repositories.sync_config_repository import SyncConfigRepository

    start_date_formatted = start_date.replace('-', '') if start_date else None

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'moneyflow_hsgt')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_moneyflow_hsgt_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_moneyflow_hsgt_full_history',
        display_name='沪深港通资金流向全量历史同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='moneyflow_hsgt_page'
    )

    logger.info(f"沪深港通资金流向全量历史同步任务已提交: {celery_task.id}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

@router.get("/latest")
@handle_api_errors
async def get_latest_moneyflow(
    current_user: User = Depends(get_current_user)
):
    """
    获取最新的资金流向数据
    """
    service = MoneyflowHsgtService()
    data = await asyncio.to_thread(service.get_latest_moneyflow)

    if not data:
        return ApiResponse.success(
            data=None,
            message="暂无资金流向数据"
        )

    return ApiResponse.success(
        data=data,
        message="获取最新资金流向成功"
    )
