"""
个股严重异常波动 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.services.stk_high_shock_service import StkHighShockService
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_stk_high_shock(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_market: Optional[str] = Query(None, description="交易所"),
    limit: int = Query(30, description="返回记录数限制")
):
    """
    获取个股严重异常波动数据

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）
        ts_code: 股票代码（可选）
        trade_market: 交易所（可选）
        limit: 返回记录数限制

    Returns:
        个股严重异常波动数据列表
    """
    try:
        service = StkHighShockService()
        result = await service.get_stk_high_shock_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            trade_market=trade_market,
            limit=limit
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取个股严重异常波动数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取个股严重异常波动统计信息

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）

    Returns:
        统计信息
    """
    try:
        service = StkHighShockService()
        stats = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取最新的个股严重异常波动数据

    Args:
        limit: 返回记录数限制

    Returns:
        最新数据列表
    """
    try:
        service = StkHighShockService()
        result = await service.get_latest_data(limit=limit)
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_high_shock_async(
    trade_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步个股严重异常波动数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个公告日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_high_shock_tasks import sync_stk_high_shock_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_stk_high_shock_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'ts_code': ts_code
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_high_shock',
            display_name='个股严重异常波动',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'ts_code': ts_code
            },
            source='stk_high_shock_page'
        )

        logger.info(f"个股严重异常波动同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交个股严重异常波动同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
