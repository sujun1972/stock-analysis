"""
卖方盈利预测数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.report_rc_service import ReportRcService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_report_rc(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="单日研报日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    org_name: Optional[str] = Query(None, description="机构名称"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向：asc/desc")
):
    """获取卖方盈利预测数据"""
    try:
        service = ReportRcService()

        # 未传日期时，自动解析最近有数据的研报日期，回传给前端回填
        resolved_date = None
        if not trade_date and not start_date and not end_date:
            resolved_date = await service.resolve_default_report_date()
            if resolved_date:
                trade_date = resolved_date

        result = await service.get_report_rc_data(
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            org_name=org_name,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        if resolved_date:
            result['report_date'] = resolved_date

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询卖方盈利预测数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取卖方盈利预测数据统计信息"""
    try:
        service = ReportRcService()
        result = await service.get_report_rc_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            page_size=1,
        )
        return ApiResponse.success(data=result.get('statistics', {}))
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """获取最新的卖方盈利预测数据"""
    try:
        service = ReportRcService()
        result = await service.get_latest_data()
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-rated")
async def get_top_rated(
    report_date: Optional[str] = Query(None, description="研报日期，格式：YYYY-MM-DD"),
    limit: int = Query(20, description="返回记录数", ge=1, le=100)
):
    """获取高评级股票"""
    try:
        service = ReportRcService()
        result = await service.get_top_rated_stocks(report_date=report_date, limit=limit)
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取高评级股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-start-date")
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
    service = ReportRcService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
async def sync_report_rc_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_date: Optional[str] = Query(None, description="研报日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步增量同步卖方盈利预测数据（Celery 任务）"""
    try:
        from app.tasks.report_rc_tasks import sync_report_rc_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        report_date_formatted = report_date.replace('-', '') if report_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 从 sync_configs 读取增量同步策略及任务限速
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'report_rc')
        sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        # 若未指定 start_date 且策略需要日期范围，自动计算建议起始日期
        if not start_date_formatted and not report_date_formatted and \
                sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date'):
            suggested = await ReportRcService().get_suggested_start_date()
            if suggested:
                start_date_formatted = suggested
                logger.info(f"卖方盈利预测增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

        celery_task = sync_report_rc_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'report_date': report_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
                'max_requests_per_minute': max_rpm,
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_report_rc',
            display_name='卖方盈利预测数据',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'report_date': report_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'sync_strategy': sync_strategy,
                'max_requests_per_minute': max_rpm,
            },
            source='report_rc_page'
        )

        logger.info(f"卖方盈利预测数据同步任务已提交: {celery_task.id} strategy={sync_strategy}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交卖方盈利预测数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_report_rc_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD 或 YYYYMMDD"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步卖方盈利预测历史数据（按月切片，Redis Set 续继）"""
    try:
        from app.tasks.report_rc_tasks import sync_report_rc_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'report_rc')

        start_date_formatted = start_date.replace('-', '') if start_date else None
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'report_rc')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_report_rc_full_history_task.apply_async(
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
            task_name='tasks.sync_report_rc_full_history',
            display_name='卖方盈利预测全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
            },
            source='report_rc_page'
        )

        logger.info(f"卖方盈利预测全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交卖方盈利预测全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
