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
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    org_name: Optional[str] = Query(None, description="机构名称"),
    limit: int = Query(30, description="返回记录数", ge=1, le=1000)
):
    """
    查询卖方盈利预测数据

    Args:
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        org_name: 机构名称
        limit: 返回记录数

    Returns:
        卖方盈利预测数据列表和统计信息
    """
    try:
        service = ReportRcService()
        result = await service.get_report_rc_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            org_name=org_name,
            limit=limit
        )

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
    """
    获取卖方盈利预测数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        service = ReportRcService()
        result = await service.get_report_rc_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=1
        )

        return ApiResponse.success(data=result.get('statistics', {}))

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新的卖方盈利预测数据

    Returns:
        最新数据
    """
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
    """
    获取高评级股票

    Args:
        report_date: 研报日期，格式：YYYY-MM-DD（可选，默认最新）
        limit: 返回记录数

    Returns:
        高评级股票列表
    """
    try:
        service = ReportRcService()
        result = await service.get_top_rated_stocks(
            report_date=report_date,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取高评级股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_report_rc_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_date: Optional[str] = Query(None, description="研报日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步卖方盈利预测数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码
        report_date: 研报日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.report_rc_tasks import sync_report_rc_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        report_date_formatted = report_date.replace('-', '') if report_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_report_rc_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'report_date': report_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
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
                'end_date': end_date_formatted
            },
            source='report_rc_page'
        )

        logger.info(f"卖方盈利预测数据同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交卖方盈利预测数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
