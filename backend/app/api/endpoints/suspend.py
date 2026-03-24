"""
停复牌信息 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.suspend_service import SuspendService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_suspend_data(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    suspend_type: Optional[str] = Query(None, description="停复牌类型：S-停牌，R-复牌"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(30, ge=1, le=100, description="每页记录数，最大100")
):
    """
    查询停复牌数据（支持分页）

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        suspend_type: 停复牌类型，S-停牌，R-复牌
        page: 页码，从1开始
        page_size: 每页记录数，最大100

    Returns:
        停复牌数据列表（包含分页信息）
    """
    try:
        service = SuspendService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        result = await service.get_suspend_data(
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            ts_code=ts_code,
            suspend_type=suspend_type,
            limit=page_size,
            page=page
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询停复牌数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取停复牌统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    try:
        service = SuspendService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        stats = await service.get_statistics(
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取停复牌统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新的交易日期

    Returns:
        最新交易日期
    """
    try:
        service = SuspendService()
        latest = await service.get_latest_trade_date()

        return ApiResponse.success(data={"latest_trade_date": latest})

    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_suspend_async(
    ts_code: Optional[str] = Query(None, description="股票代码（可输入多值，逗号分隔）"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    suspend_type: Optional[str] = Query(None, description="停复牌类型：S-停牌，R-复牌"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步停复牌数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可输入多值，逗号分隔）
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        suspend_type: 停复牌类型，S-停牌，R-复牌
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.suspend_tasks import sync_suspend_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_suspend_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'suspend_type': suspend_type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_suspend',
            display_name='每日停复牌信息',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'suspend_type': suspend_type
            },
            source='suspend_page'
        )

        logger.info(f"停复牌信息同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交停复牌信息同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
