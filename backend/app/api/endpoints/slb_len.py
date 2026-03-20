"""
转融资交易汇总 API
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.slb_len_service import SlbLenService

router = APIRouter()


@router.get("")
async def get_slb_len_data(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=5000, description="返回记录数（最大5000）")
):
    """
    获取转融资交易汇总数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        limit: 返回记录数（默认30，最大5000）

    Returns:
        转融资交易汇总数据列表
    """
    try:
        slb_len_service = SlbLenService()
        result = await slb_len_service.get_slb_len_data(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取转融资交易汇总数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_slb_len_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取转融资交易汇总统计数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计数据（平均期末余额、最大期末余额、最小期末余额、累计竞价成交等）
    """
    try:
        slb_len_service = SlbLenService()
        result = await slb_len_service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取转融资统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_slb_len():
    """
    获取最新交易日的转融资数据

    Returns:
        最新交易日的转融资数据
    """
    try:
        slb_len_service = SlbLenService()
        result = await slb_len_service.get_latest_data()

        if result is None:
            return ApiResponse.success(
                data={},
                message="暂无数据"
            )

        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新转融资数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_slb_len_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步转融资交易汇总数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.slb_len_tasks import sync_slb_len_task
        from app.services import TaskHistoryHelper

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_slb_len_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_slb_len',
            display_name='转融资交易汇总',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='slb_len_page'
        )

        logger.info(f"转融资交易汇总同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交转融资交易汇总同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
