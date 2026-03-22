"""
业绩预告数据API端点
"""

import asyncio
import json
from typing import Optional
from datetime import date
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.forecast_service import ForecastService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.get("")
async def get_forecast(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    type: Optional[str] = Query(None, description="预告类型，如：预增、预减、扭亏、首亏"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制")
):
    """
    查询业绩预告数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        period: 报告期（可选）
        type: 预告类型（可选）
        limit: 返回记录数限制

    Returns:
        业绩预告数据列表
    """
    try:
        service = ForecastService()
        result = await service.get_forecast_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            period=period,
            type_=type,
            limit=limit
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询业绩预告数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    type: Optional[str] = Query(None, description="预告类型，如：预增、预减、扭亏、首亏")
):
    """
    获取业绩预告统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        type: 预告类型（可选）

    Returns:
        统计信息
    """
    try:
        service = ForecastService()
        statistics = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            type_=type
        )
        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取业绩预告统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH")
):
    """
    获取最新业绩预告数据

    Args:
        ts_code: 股票代码（可选）

    Returns:
        最新业绩预告记录
    """
    try:
        service = ForecastService()
        latest = await service.get_latest_data(ts_code=ts_code)
        return ApiResponse.success(data=latest)

    except Exception as e:
        logger.error(f"获取最新业绩预告数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_forecast_async(
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    type: Optional[str] = Query(None, description="预告类型，如：预增、预减、扭亏、首亏"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步业绩预告数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ann_date: 公告日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        period: 报告期，格式：YYYY-MM-DD
        type: 预告类型（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.forecast_tasks import sync_forecast_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None
        period_formatted = period.replace('-', '') if period else None

        # 提交Celery任务（异步执行）
        celery_task = sync_forecast_task.apply_async(
            kwargs={
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted,
                'type_': type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_forecast',
            display_name='业绩预告数据',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted,
                'type': type
            },
            source='forecast_page'
        )

        logger.info(f"业绩预告同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交业绩预告同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
