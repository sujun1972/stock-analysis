"""
神奇九转指标数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.stk_nineturn_service import StkNineturnService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_stk_nineturn(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    freq: str = Query('daily', description="频率（daily）"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=10000),
    sort_by: Optional[str] = Query(None, description="排序字段（up_count/down_count/close/trade_date）"),
    sort_order: Optional[str] = Query(None, description="排序方向（asc/desc）")
):
    """
    查询神奇九转指标数据

    Returns:
        神奇九转指标数据列表和统计信息
    """
    try:
        service = StkNineturnService()
        result = await service.get_stk_nineturn_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            limit=page_size,
            offset=(page - 1) * page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询神奇九转指标数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    freq: str = Query('daily', description="频率（daily）")
):
    """
    获取神奇九转指标统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        freq: 频率，默认daily

    Returns:
        统计信息
    """
    try:
        service = StkNineturnService()
        result = await service.get_stk_nineturn_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            limit=1
        )

        return ApiResponse.success(data=result.get('statistics', {}))

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新交易日期

    Args:
        ts_code: 股票代码（可选）

    Returns:
        最新交易日期
    """
    try:
        service = StkNineturnService()
        latest_date = await service.get_latest_date(ts_code=ts_code)

        return ApiResponse.success(data={'latest_date': latest_date})

    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_turn_signals(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    signal_type: str = Query('all', description="信号类型（up:上九转, down:下九转, all:全部）"),
    limit: int = Query(50, description="返回记录数", ge=1, le=1000)
):
    """
    获取九转信号（+9或-9）

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        signal_type: 信号类型 ('up': 上九转, 'down': 下九转, 'all': 全部)
        limit: 返回记录数

    Returns:
        九转信号列表
    """
    try:
        service = StkNineturnService()
        signals = await service.get_turn_signals(
            start_date=start_date,
            end_date=end_date,
            signal_type=signal_type,
            limit=limit
        )

        return ApiResponse.success(data={'items': signals, 'total': len(signals)})

    except Exception as e:
        logger.error(f"获取九转信号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-start-date")
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始日期（YYYYMMDD）。"""
    service = StkNineturnService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
async def sync_stk_nineturn_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    freq: str = Query('daily', description="频率（daily）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步神奇九转指标数据（通过Celery任务）"""
    try:
        from app.tasks.stk_nineturn_tasks import sync_stk_nineturn_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 从 sync_configs 读取增量同步策略及限速
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_nineturn')
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        # 若未指定 start_date，自动计算建议起始日期
        if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
            suggested = await StkNineturnService().get_suggested_start_date()
            if suggested:
                start_date_formatted = suggested
                logger.info(f"神奇九转指标增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

        celery_task = sync_stk_nineturn_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'freq': freq,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
                'max_requests_per_minute': max_rpm,
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_nineturn',
            display_name='神奇九转指标',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'freq': freq,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
            },
            source='stk_nineturn_page'
        )

        logger.info(f"神奇九转指标同步任务已提交: {celery_task.id} strategy={sync_strategy}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交神奇九转指标同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_stk_nineturn_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步神奇九转指标历史数据（按月切片，Redis Set 续继）"""
    try:
        from app.tasks.stk_nineturn_tasks import sync_stk_nineturn_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'stk_nineturn')

        start_date_formatted = start_date.replace('-', '') if start_date else None
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_nineturn')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_stk_nineturn_full_history_task.apply_async(
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
            task_name='tasks.sync_stk_nineturn_full_history',
            display_name='神奇九转指标全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
            },
            source='stk_nineturn_page'
        )

        logger.info(f"神奇九转指标全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交神奇九转指标全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
