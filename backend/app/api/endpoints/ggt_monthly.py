"""
港股通每月成交统计 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.ggt_monthly_service import GgtMonthlyService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_ggt_monthly(
    start_month: Optional[str] = Query(None, description="开始月度，格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度，格式：YYYY-MM"),
    limit: int = Query(30, description="每页记录数"),
    offset: int = Query(0, description="分页偏移量")
):
    """
    查询港股通每月成交统计数据

    Args:
        start_month: 开始月度，格式：YYYY-MM
        end_month: 结束月度，格式：YYYY-MM
        limit: 每页记录数
        offset: 分页偏移量

    Returns:
        港股通每月成交统计数据列表
    """
    service = GgtMonthlyService()
    result = await service.get_data(
        start_month=start_month,
        end_month=end_month,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_month: Optional[str] = Query(None, description="开始月度，格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度，格式：YYYY-MM")
):
    """
    获取港股通每月成交统计信息

    Args:
        start_month: 开始月度，格式：YYYY-MM
        end_month: 结束月度，格式：YYYY-MM

    Returns:
        统计信息
    """
    service = GgtMonthlyService()
    # 转换月度格式
    start_month_fmt = start_month.replace('-', '') if start_month else None
    end_month_fmt = end_month.replace('-', '') if end_month else None

    # 获取统计信息
    result = await asyncio.to_thread(
        service.ggt_monthly_repo.get_statistics,
        start_month=start_month_fmt,
        end_month=end_month_fmt
    )
    return ApiResponse.success(data=result)

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新港股通每月成交统计数据

    Returns:
        最新数据
    """
    service = GgtMonthlyService()
    result = await service.get_latest_data()
    return ApiResponse.success(data=result)

@router.post("/sync-async")
@handle_api_errors
async def sync_ggt_monthly_async(
    month: Optional[str] = Query(None, description="月度，格式：YYYY-MM，支持多月逗号分隔"),
    start_month: Optional[str] = Query(None, description="开始月度，格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度，格式：YYYY-MM"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步港股通每月成交统计数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        month: 月度，格式：YYYY-MM，支持多月逗号分隔（如：2024-01,2024-02）
        start_month: 开始月度，格式：YYYY-MM
        end_month: 结束月度，格式：YYYY-MM
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.ggt_monthly_tasks import sync_ggt_monthly_task

    # 转换月度格式：YYYY-MM -> YYYYMM（Tushare格式）
    month_formatted = month.replace('-', '') if month else None
    start_month_formatted = start_month.replace('-', '') if start_month else None
    end_month_formatted = end_month.replace('-', '') if end_month else None

    # 提交Celery任务（异步执行）
    celery_task = sync_ggt_monthly_task.apply_async(
        kwargs={
            'month': month_formatted,
            'start_month': start_month_formatted,
            'end_month': end_month_formatted
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_ggt_monthly',
        display_name='港股通每月成交统计',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'month': month_formatted,
            'start_month': start_month_formatted,
            'end_month': end_month_formatted
        },
        source='ggt_monthly_page'
    )

    logger.info(f"港股通每月成交统计同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_ggt_monthly_full_history(
    current_user: User = Depends(require_admin)
):
    """
    全量同步港股通每月成交统计历史数据（snapshot 策略）

    数据量极小（约74条），不传日期参数直接获取全量，单次请求完成。

    Returns:
        包含 Celery 任务 ID 和任务信息的响应
    """
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'ggt_monthly')

    from app.tasks.ggt_monthly_tasks import sync_ggt_monthly_full_history_task

    celery_task = sync_ggt_monthly_full_history_task.apply_async(kwargs={})

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_ggt_monthly_full_history',
        display_name='港股通每月成交统计（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='ggt_monthly_page'
    )

    logger.info(f"港股通每月成交统计全量同步任务已提交: {celery_task.id}")
    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
