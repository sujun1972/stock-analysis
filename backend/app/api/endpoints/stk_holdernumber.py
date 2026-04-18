"""
股东人数API端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.stk_holdernumber_service import StkHolderNumberService
from app.services import TaskHistoryHelper
from app.models.user import User
from app.core.dependencies import require_admin
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_stk_holdernumber(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """获取股东人数数据"""
    service = StkHolderNumberService()
    result = await service.get_stk_holdernumber_data(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取股东人数统计信息"""
    service = StkHolderNumberService()
    stats = await service.get_statistics(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse.success(data=stats)

@router.get("/latest/{ts_code}")
@handle_api_errors
async def get_latest(
    ts_code: str,
    limit: int = Query(10, description="返回记录数限制")
):
    """获取指定股票的最新股东人数数据"""
    service = StkHolderNumberService()
    result = await service.get_latest_by_code(ts_code=ts_code, limit=limit)
    return ApiResponse.success(data=result)

@router.get("/suggest-start-date")
@handle_api_errors
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """
    返回增量同步的建议起始日期（YYYYMMDD）。

    计算规则：
      候选起始 = 今天 - incremental_default_days（sync_configs 中配置）
      上次结束 = sync_history 中最近一次增量成功的 data_end_date
      建议起始 = min(候选起始, 上次结束)，取更早者保证数据连续
    """
    service = StkHolderNumberService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-full-history")
@handle_api_errors
async def sync_stk_holdernumber_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从2009年开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步股东人数历史数据（支持中断续继，切片策略从 sync_configs.full_sync_strategy 读取）"""
    from app.tasks.stk_holdernumber_tasks import sync_stk_holdernumber_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'stk_holdernumber')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'stk_holdernumber')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
    strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    celery_task = sync_stk_holdernumber_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency,
                'strategy': strategy, 'max_requests_per_minute': max_rpm}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_stk_holdernumber_full_history',
        display_name='股东人数（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency,
                     'strategy': strategy, 'max_requests_per_minute': max_rpm},
        source='stk_holdernumber_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")

@router.post("/sync-async")
@handle_api_errors
async def sync_stk_holdernumber_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步增量同步股东人数数据（Celery 任务）"""
    from app.tasks.stk_holdernumber_tasks import sync_stk_holdernumber_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    ann_date_formatted = ann_date.replace('-', '') if ann_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 从 sync_configs 读取增量同步策略及任务限速
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_holdernumber')
    sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    # 若未指定 start_date 且策略需要日期范围，自动计算建议起始日期
    if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date'):
        suggested = await StkHolderNumberService().get_suggested_start_date()
        if suggested:
            start_date_formatted = suggested
            logger.info(f"股东人数增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

    celery_task = sync_stk_holdernumber_task.apply_async(
        kwargs={
            'ts_code': ts_code,
            'ann_date': ann_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_stk_holdernumber',
        display_name='股东人数',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code,
            'ann_date': ann_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        },
        source='stk_holdernumber_page'
    )

    logger.info(f"股东人数增量同步任务已提交: {celery_task.id} strategy={sync_strategy}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")
