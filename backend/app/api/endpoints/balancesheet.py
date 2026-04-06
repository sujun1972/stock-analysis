"""
资产负债表数据API端点
"""

import asyncio
from fastapi import APIRouter, Query, Depends
from typing import Optional
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.balancesheet_service import BalancesheetService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_balancesheet_data(
    start_date: Optional[str] = Query(None, description="开始日期（公告日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（公告日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    report_type: Optional[str] = Query(None, description="报告类型（1-12）"),
    limit: int = Query(30, ge=1, le=1000, description="限制返回记录数"),
    offset: int = Query(0, ge=0, description="分页偏移量")
):
    """
    查询资产负债表数据

    Args:
        start_date: 开始日期（公告日期）
        end_date: 结束日期（公告日期）
        ts_code: 股票代码
        period: 报告期
        report_type: 报告类型
        limit: 限制返回记录数

    Returns:
        资产负债表数据列表
    """
    try:
        service = BalancesheetService()
        result = await service.get_balancesheet_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            period=period,
            report_type=report_type,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询资产负债表数据失败: {e}")
        return ApiResponse.error(message=f"查询失败: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（公告日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（公告日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取资产负债表统计信息

    Args:
        start_date: 开始日期（公告日期）
        end_date: 结束日期（公告日期）
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        service = BalancesheetService()
        result = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取资产负债表统计信息失败: {e}")
        return ApiResponse.error(message=f"获取统计信息失败: {str(e)}")


@router.get("/latest")
async def get_latest_balancesheet(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新资产负债表数据

    Args:
        ts_code: 股票代码

    Returns:
        最新资产负债表记录
    """
    try:
        service = BalancesheetService()
        result = await service.get_latest_data(ts_code=ts_code)

        if result:
            return ApiResponse.success(data=result)
        else:
            return ApiResponse.success(data=None, message="暂无数据")

    except Exception as e:
        logger.error(f"获取最新资产负债表数据失败: {e}")
        return ApiResponse.error(message=f"获取最新数据失败: {str(e)}")


@router.post("/sync-async")
async def sync_balancesheet_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    report_type: Optional[str] = Query('1', description="报告类型（1-12），默认1-合并报表"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步资产负债表数据（使用 Celery）

    Args:
        ts_code: 股票代码
        period: 报告期（如 2023-12-31 表示年报）
        start_date: 开始日期
        end_date: 结束日期
        report_type: 报告类型
        current_user: 当前用户

    Returns:
        任务信息
    """
    try:
        from app.tasks.balancesheet_tasks import sync_balancesheet_task

        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        period_fmt = period.replace('-', '') if period else None
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 提交 Celery 任务
        celery_task = sync_balancesheet_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'period': period_fmt,
                'start_date': start_date_fmt,
                'end_date': end_date_fmt,
                'report_type': report_type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_balancesheet',
            display_name='资产负债表数据同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'period': period_fmt,
                'start_date': start_date_fmt,
                'end_date': end_date_fmt,
                'report_type': report_type
            },
            source='balancesheet_page'
        )

        return ApiResponse.success(
            data=task_data,
            message="资产负债表同步任务已提交，请在任务面板查看进度"
        )

    except Exception as e:
        logger.error(f"提交资产负债表同步任务失败: {e}")
        return ApiResponse.error(message=f"任务提交失败: {str(e)}")


@router.post("/sync-full-history-async")
async def sync_balancesheet_full_history_async(
    start_date: Optional[str] = Query(None, description="起始日期（YYYYMMDD），不传则从系统配置读取"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    异步全量同步资产负债表历史数据（按季度 period 切片 + Redis 续继）

    Args:
        start_date: 起始日期 YYYYMMDD，不传则由前端传入系统配置的 earliest_history_date
        concurrency: 并发数，不传则从 sync_configs 读取
        current_user: 当前用户

    Returns:
        任务信息
    """
    try:
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'balancesheet')
        from app.tasks.balancesheet_tasks import sync_balancesheet_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'balancesheet')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_balancesheet_full_history_task.apply_async(
            kwargs={'start_date': start_date, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_balancesheet_full_history',
            display_name='资产负债表全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date, 'concurrency': concurrency},
            source='balancesheet_page'
        )

        return ApiResponse.success(
            data=task_data,
            message="资产负债表全量同步任务已提交，请在任务面板查看进度"
        )

    except Exception as e:
        logger.error(f"提交资产负债表全量同步任务失败: {e}")
        return ApiResponse.error(message=f"任务提交失败: {str(e)}")
