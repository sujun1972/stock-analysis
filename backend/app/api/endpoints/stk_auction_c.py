"""
股票收盘集合竞价数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.stk_auction_c_service import StkAuctionCService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_stk_auction_c(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(30, description="每页记录数", ge=1, le=1000),
    limit: int = Query(None, description="返回记录数（兼容旧参数）", ge=1, le=1000),
    offset: int = Query(None, description="偏移量（兼容旧参数）", ge=0)
):
    """
    查询股票收盘集合竞价数据

    说明：每天盘后更新，单次请求最大返回10000行数据

    Returns:
        收盘集合竞价数据列表和统计信息，含 trade_date 用于前端回填
    """
    try:
        service = StkAuctionCService()

        # 转换日期格式
        trade_date_fmt = trade_date.replace('-', '') if trade_date else None
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 分页参数（兼容旧 limit/offset）
        actual_limit = limit if limit is not None else page_size
        actual_offset = offset if offset is not None else (page - 1) * page_size

        # 未传日期时自动解析最近有数据的交易日
        resolved_date = None
        if not trade_date_fmt and not start_date_fmt and not end_date_fmt:
            resolved_date = await service.resolve_default_trade_date()
            if resolved_date:
                trade_date_fmt = resolved_date.replace('-', '')

        # 调用服务
        result = await service.get_stk_auction_c_data(
            ts_code=ts_code,
            trade_date=trade_date_fmt,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            limit=actual_limit,
            offset=actual_offset
        )

        # 回传 trade_date 供前端回填日期选择器
        if resolved_date:
            result['trade_date'] = resolved_date

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询收盘集合竞价数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取收盘集合竞价数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    try:
        service = StkAuctionCService()

        # 转换日期格式
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 查询统计信息
        statistics = await asyncio.to_thread(
            service.stk_auction_c_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新的收盘集合竞价数据

    Returns:
        最新数据
    """
    try:
        service = StkAuctionCService()
        result = await service.get_latest_data()

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-start-date")
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始日期（YYYYMMDD）。"""
    service = StkAuctionCService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
async def sync_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步股票收盘集合竞价数据（通过Celery任务）"""
    try:
        from app.tasks.stk_auction_c_tasks import sync_stk_auction_c_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 从 sync_configs 读取增量同步策略及限速
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_auction_c')
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        # 若未指定 start_date，自动计算建议起始日期
        if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
            suggested = await StkAuctionCService().get_suggested_start_date()
            if suggested:
                start_date_formatted = suggested
                logger.info(f"收盘集合竞价增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

        celery_task = sync_stk_auction_c_task.apply_async(
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
            task_name='tasks.sync_stk_auction_c',
            display_name='股票收盘集合竞价',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
            },
            source='stk_auction_c_page'
        )

        logger.info(f"股票收盘集合竞价数据同步任务已提交: {celery_task.id} strategy={sync_strategy}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交股票收盘集合竞价数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_stk_auction_c_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步股票收盘集合竞价历史数据（按月切片，Redis Set 续继）"""
    try:
        from app.tasks.stk_auction_c_tasks import sync_stk_auction_c_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'stk_auction_c')

        start_date_formatted = start_date.replace('-', '') if start_date else None
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'stk_auction_c')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_stk_auction_c_full_history_task.apply_async(
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
            task_name='tasks.sync_stk_auction_c_full_history',
            display_name='股票收盘集合竞价全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
            },
            source='stk_auction_c_page'
        )

        logger.info(f"股票收盘集合竞价全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交股票收盘集合竞价全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
