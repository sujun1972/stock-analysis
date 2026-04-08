"""
个股异常波动 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.services.stk_shock_service import StkShockService
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_stk_shock(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    获取个股异常波动数据

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）
        ts_code: 股票代码（可选）
        limit: 返回记录数限制

    Returns:
        个股异常波动数据列表
    """
    try:
        service = StkShockService()
        result = await service.get_stk_shock_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取个股异常波动数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取个股异常波动统计信息

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）

    Returns:
        统计信息
    """
    try:
        service = StkShockService()
        stats = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取最新的个股异常波动数据

    Args:
        limit: 返回记录数限制

    Returns:
        最新数据列表
    """
    try:
        service = StkShockService()
        result = await service.get_latest_data(limit=limit)
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_stk_shock_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从 sync_configs 读取"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步个股异常波动历史数据（按月切片，支持 Redis 续继，策略从 sync_configs 读取）"""
    try:
        from app.tasks.stk_shock_tasks import sync_stk_shock_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'stk_shock')

        start_date_formatted = start_date.replace('-', '') if start_date else None

        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'stk_shock')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_stk_shock_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency,
                    'strategy': strategy, 'max_requests_per_minute': max_rpm}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_shock_full_history',
            display_name='个股异常波动（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted, 'concurrency': concurrency,
                         'strategy': strategy, 'max_requests_per_minute': max_rpm},
            source='stk_shock_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")
    except Exception as e:
        logger.error(f"提交个股异常波动全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_shock_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    current_user: User = Depends(require_admin)
):
    """异步增量同步个股异常波动数据（Celery 任务）"""
    try:
        from app.tasks.stk_shock_tasks import sync_stk_shock_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_shock')
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
            from app.services.stk_shock_service import StkShockService
            suggested = await StkShockService().get_suggested_start_date()
            if suggested:
                start_date_formatted = suggested
                logger.info(f"个股异常波动增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

        celery_task = sync_stk_shock_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'ts_code': ts_code,
                'sync_strategy': sync_strategy,
                'max_requests_per_minute': max_rpm,
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_shock',
            display_name='个股异常波动',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'ts_code': ts_code,
                'sync_strategy': sync_strategy,
            },
            source='stk_shock_page'
        )

        logger.info(f"个股异常波动增量同步任务已提交: {celery_task.id} strategy={sync_strategy}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交个股异常波动同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
