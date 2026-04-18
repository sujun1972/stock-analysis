"""
机构调研表 API 端点
"""

import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.stk_surv_service import StkSurvService
from app.services import TaskHistoryHelper
from app.models.user import User
from app.core.dependencies import require_admin
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_stk_surv(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    org_type: Optional[str] = Query(None, description="接待公司类型"),
    rece_mode: Optional[str] = Query(None, description="接待方式"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(30, description="每页记录数", ge=1, le=1000),
    limit: Optional[int] = Query(None, description="返回记录数（兼容旧参数）", ge=1, le=1000)
):
    """
    查询机构调研数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        org_type: 接待公司类型（可选）
        rece_mode: 接待方式（可选）
        page: 页码
        page_size: 每页记录数
        limit: 返回记录数（兼容旧参数）

    Returns:
        机构调研数据列表
    """
    actual_limit = limit if limit is not None else page_size
    actual_offset = (page - 1) * page_size if limit is None else 0

    service = StkSurvService()
    result = await service.get_stk_surv_data(
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        org_type=org_type,
        rece_mode=rece_mode,
        limit=actual_limit,
        offset=actual_offset
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取机构调研统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    service = StkSurvService()
    stats = await service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse.success(data=stats)

@router.get("/latest")
@handle_api_errors
async def get_latest(
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取最新的机构调研数据

    Args:
        limit: 返回记录数限制

    Returns:
        最新机构调研数据列表
    """
    service = StkSurvService()
    result = await service.get_latest_data(limit=limit)
    return ApiResponse.success(data=result)

@router.get("/suggest-start-date")
@handle_api_errors
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始日期（YYYYMMDD）。"""
    service = StkSurvService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
@handle_api_errors
async def sync_stk_surv_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="调研日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="调研开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="调研结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步机构调研数据（通过Celery任务）"""
    from app.tasks.stk_surv_tasks import sync_stk_surv_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 从 sync_configs 读取增量同步策略及限速
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_surv')
    sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    # 若未指定 start_date，自动计算建议起始日期
    if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
        suggested = await StkSurvService().get_suggested_start_date()
        if suggested:
            start_date_formatted = suggested
            logger.info(f"机构调研增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

    celery_task = sync_stk_surv_task.apply_async(
        kwargs={
            'ts_code': ts_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_stk_surv',
        display_name='机构调研表',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
        },
        source='stk_surv_page'
    )

    logger.info(f"机构调研数据同步任务已提交: {celery_task.id} strategy={sync_strategy}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

@router.post("/sync-full-history")
@handle_api_errors
async def sync_stk_surv_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步机构调研历史数据（按月切片，Redis Set 续继）"""
    from app.tasks.stk_surv_tasks import sync_stk_surv_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock

    await asyncio.to_thread(release_stale_lock, 'stk_surv')

    start_date_formatted = start_date.replace('-', '') if start_date else None
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_surv')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
    strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    celery_task = sync_stk_surv_full_history_task.apply_async(
        kwargs={
            'start_date': start_date_formatted,
            'concurrency': concurrency,
            'strategy': strategy,
            'max_requests_per_minute': max_rpm,
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_stk_surv_full_history',
        display_name='机构调研全量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'start_date': start_date_formatted,
            'concurrency': concurrency,
            'strategy': strategy,
        },
        source='stk_surv_page'
    )

    logger.info(f"机构调研全量同步任务已提交: {celery_task.id}")
    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
