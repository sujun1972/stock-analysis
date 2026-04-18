"""
每日筹码及胜率数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.cyq_perf_service import CyqPerfService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_cyq_perf(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向：asc/desc")
):
    """
    查询筹码及胜率数据

    Returns:
        筹码及胜率数据列表、统计信息、总数和默认日期
    """
    service = CyqPerfService()

    # 未传日期时，自动解析最近有数据的交易日期，回传给前端回填
    resolved_date = None
    if not trade_date and not start_date and not end_date:
        resolved_date = await service.resolve_default_trade_date()
        if resolved_date:
            trade_date = resolved_date

    result = await service.get_cyq_perf_data(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        trade_date=trade_date,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # 回传解析出的日期，供前端回填日期选择器
    if resolved_date:
        result['trade_date'] = resolved_date

    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取筹码及胜率数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    service = CyqPerfService()
    result = await service.get_cyq_perf_data(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        page_size=1
    )

    return ApiResponse.success(data=result.get('statistics', {}))

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新的筹码及胜率数据

    Returns:
        最新数据
    """
    service = CyqPerfService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)

@router.get("/top-winner")
@handle_api_errors
async def get_top_winner(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    limit: int = Query(20, description="返回记录数", ge=1, le=100)
):
    """
    获取高胜率股票

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD（可选，默认最新）
        limit: 返回记录数

    Returns:
        高胜率股票列表
    """
    service = CyqPerfService()
    result = await service.get_top_winner_stocks(
        trade_date=trade_date,
        limit=limit
    )

    return ApiResponse.success(data=result)

@router.get("/suggest-start-date")
@handle_api_errors
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始日期（YYYYMMDD）。"""
    service = CyqPerfService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
@handle_api_errors
async def sync_cyq_perf_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步筹码及胜率数据（通过Celery任务）"""
    from app.tasks.cyq_perf_tasks import sync_cyq_perf_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 从 sync_configs 读取增量同步策略及限速
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'cyq_perf')
    sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_ts_code') if cfg else 'by_ts_code'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    # 若未指定 start_date 且策略需要日期范围，自动计算建议起始日期
    if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
        suggested = await CyqPerfService().get_suggested_start_date()
        if suggested:
            start_date_formatted = suggested
            logger.info(f"筹码及胜率增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

    celery_task = sync_cyq_perf_task.apply_async(
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
        task_name='tasks.sync_cyq_perf',
        display_name='每日筹码及胜率',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
        },
        source='cyq_perf_page'
    )

    logger.info(f"筹码及胜率数据同步任务已提交: {celery_task.id} strategy={sync_strategy}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

@router.post("/sync-full-history")
@handle_api_errors
async def sync_cyq_perf_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步每日筹码及胜率历史数据（逐只股票请求，Redis Set 续继）"""
    from app.tasks.cyq_perf_tasks import sync_cyq_perf_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock

    await asyncio.to_thread(release_stale_lock, 'cyq_perf')

    start_date_formatted = start_date.replace('-', '') if start_date else None
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'cyq_perf')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
    strategy = (cfg.get('full_sync_strategy') or 'by_ts_code') if cfg else 'by_ts_code'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    celery_task = sync_cyq_perf_full_history_task.apply_async(
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
        task_name='tasks.sync_cyq_perf_full_history',
        display_name='每日筹码及胜率全量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'start_date': start_date_formatted,
            'concurrency': concurrency,
            'strategy': strategy,
        },
        source='cyq_perf_page'
    )

    logger.info(f"每日筹码及胜率全量同步任务已提交: {celery_task.id}")
    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
