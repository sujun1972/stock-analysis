"""
港股通每月成交统计 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.ggt_monthly_service import GgtMonthlyService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_ggt_monthly(
    start_month: Optional[str] = Query(None, description="开始月度，格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度，格式：YYYY-MM"),
    limit: int = Query(30, description="返回记录数限制")
):
    """
    查询港股通每月成交统计数据

    Args:
        start_month: 开始月度，格式：YYYY-MM
        end_month: 结束月度，格式：YYYY-MM
        limit: 返回记录数限制

    Returns:
        港股通每月成交统计数据列表
    """
    try:
        service = GgtMonthlyService()
        result = await service.get_data(
            start_month=start_month,
            end_month=end_month,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"查询港股通每月成交统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
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
    try:
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
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新港股通每月成交统计数据

    Returns:
        最新数据
    """
    try:
        service = GgtMonthlyService()
        result = await service.get_latest_data()
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
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
    try:
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

    except Exception as e:
        logger.error(f"提交港股通每月成交统计同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
