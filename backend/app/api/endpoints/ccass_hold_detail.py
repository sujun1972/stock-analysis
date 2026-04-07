"""
中央结算系统持股明细数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.ccass_hold_detail_service import CcassHoldDetailService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_ccass_hold_detail(
    ts_code: Optional[str] = Query(None, description="股票代码（如 00960.HK）"),
    col_participant_id: Optional[str] = Query(None, description="参与者编号（如 B01777）"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向：asc/desc")
):
    """
    查询中央结算系统持股明细数据

    Returns:
        中央结算系统持股明细数据列表、统计信息、总数和默认日期
    """
    try:
        service = CcassHoldDetailService()

        # 未传日期时，自动解析最近有数据的交易日期，回传给前端回填
        resolved_date = None
        if not trade_date and not start_date and not end_date:
            resolved_date = await service.resolve_default_trade_date()
            if resolved_date:
                trade_date = resolved_date

        result = await service.get_ccass_hold_detail_data(
            ts_code=ts_code,
            col_participant_id=col_participant_id,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        # 回传解析出的日期，供前端回填日期选择器
        if resolved_date:
            result['trade_date'] = resolved_date

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询中央结算系统持股明细数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取中央结算系统持股明细数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        # 日期格式转换
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        service = CcassHoldDetailService()
        result = await service.get_ccass_hold_detail_data(
            ts_code=ts_code,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            limit=1
        )

        return ApiResponse.success(data=result.get('statistics', {}))

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(10, description="返回记录数", ge=1, le=100)
):
    """
    获取最新的中央结算系统持股明细数据

    Args:
        ts_code: 股票代码
        limit: 返回记录数

    Returns:
        最新数据
    """
    try:
        service = CcassHoldDetailService()
        result = await service.get_latest_data(
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-participants")
async def get_top_participants(
    trade_date: str = Query(..., description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(20, description="返回记录数", ge=1, le=100)
):
    """
    获取指定日期持股量排名前N的机构

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        limit: 返回记录数

    Returns:
        持股量排名列表
    """
    try:
        # 日期格式转换
        trade_date_fmt = trade_date.replace('-', '')

        service = CcassHoldDetailService()
        result = await service.get_top_participants(
            trade_date=trade_date_fmt,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取持股量排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-start-date")
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始日期（YYYYMMDD）。"""
    service = CcassHoldDetailService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
async def sync_ccass_hold_detail_async(
    ts_code: Optional[str] = Query(None, description="股票代码（如 00960.HK）"),
    hk_code: Optional[str] = Query(None, description="港交所代码（如 95009）"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步中央结算系统持股明细数据（通过Celery任务）"""
    try:
        from app.tasks.ccass_hold_detail_tasks import sync_ccass_hold_detail_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 从 sync_configs 读取增量同步策略及限速
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'ccass_hold_detail')
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        # 若未指定 start_date，自动计算建议起始日期
        if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
            suggested = await CcassHoldDetailService().get_suggested_start_date()
            if suggested:
                start_date_formatted = suggested
                logger.info(f"CCASS持股明细增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

        celery_task = sync_ccass_hold_detail_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'hk_code': hk_code,
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
            task_name='tasks.sync_ccass_hold_detail',
            display_name='中央结算系统持股明细',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'hk_code': hk_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
            },
            source='ccass_hold_detail_page'
        )

        logger.info(f"CCASS持股明细数据同步任务已提交: {celery_task.id} strategy={sync_strategy}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交中央结算系统持股明细数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_ccass_hold_detail_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步中央结算系统持股明细历史数据（按月切片，Redis Set 续继）"""
    try:
        from app.tasks.ccass_hold_detail_tasks import sync_ccass_hold_detail_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'ccass_hold_detail')

        start_date_formatted = start_date.replace('-', '') if start_date else None
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'ccass_hold_detail')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_ccass_hold_detail_full_history_task.apply_async(
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
            task_name='tasks.sync_ccass_hold_detail_full_history',
            display_name='中央结算系统持股明细全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
            },
            source='ccass_hold_detail_page'
        )

        logger.info(f"中央结算系统持股明细全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交中央结算系统持股明细全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
