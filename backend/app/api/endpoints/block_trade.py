"""
大宗交易数据API端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.block_trade_service import BlockTradeService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User


router = APIRouter()


@router.get("")
@handle_api_errors
async def get_block_trade(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """查询大宗交易数据"""
    service = BlockTradeService()
    result = await service.get_block_trade_data(
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        ts_code=ts_code,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取大宗交易统计信息"""
    service = BlockTradeService()
    statistics = await service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse.success(data=statistics)

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """获取最新大宗交易数据"""
    service = BlockTradeService()
    latest = await service.get_latest_data()
    return ApiResponse.success(data=latest)

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
    service = BlockTradeService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-full-history")
@handle_api_errors
async def sync_block_trade_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从2010年开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步大宗交易历史数据（支持中断续继，切片策略从 sync_configs.full_sync_strategy 读取）"""
    from app.tasks.block_trade_tasks import sync_block_trade_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'block_trade')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'block_trade')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
    strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    celery_task = sync_block_trade_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency,
                'strategy': strategy, 'max_requests_per_minute': max_rpm}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_block_trade_full_history',
        display_name='大宗交易（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency,
                     'strategy': strategy, 'max_requests_per_minute': max_rpm},
        source='block_trade_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")

@router.post("/sync-async")
@handle_api_errors
async def sync_block_trade_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    current_user: User = Depends(require_admin)
):
    """异步增量同步大宗交易数据（Celery 任务）"""
    from app.tasks.block_trade_tasks import sync_block_trade_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 从 sync_configs 读取增量同步策略及任务限速
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'block_trade')
    sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    # 若未指定 start_date 且策略需要日期范围，自动计算建议起始日期
    if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date'):
        suggested = await BlockTradeService().get_suggested_start_date()
        if suggested:
            start_date_formatted = suggested
            logger.info(f"大宗交易增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

    celery_task = sync_block_trade_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_block_trade',
        display_name='大宗交易数据',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        },
        source='block_trade_page'
    )

    logger.info(f"大宗交易增量同步任务已提交: {celery_task.id} strategy={sync_strategy}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")
