"""
财务审计意见数据 API 端点

Author: Claude
Date: 2026-03-22
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.fina_audit_service import FinaAuditService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_fina_audit(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=1000, description="限制返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    查询财务审计意见数据

    Args:
        ts_code: 股票代码
        ann_date: 公告日期
        start_date: 开始日期
        end_date: 结束日期
        period: 报告期
        limit: 限制返回记录数

    Returns:
        财务审计意见数据列表和统计信息
    """
    try:
        service = FinaAuditService()

        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        ann_date_fmt = ann_date.replace('-', '') if ann_date else None
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None
        period_fmt = period.replace('-', '') if period else None

        result = await service.get_fina_audit_data(
            ts_code=ts_code,
            ann_date=ann_date_fmt,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            period=period_fmt,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询财务审计意见数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_fina_audit_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取财务审计意见统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计信息
    """
    try:
        service = FinaAuditService()

        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        statistics = await asyncio.to_thread(
            service.fina_audit_repo.get_statistics,
            start_date_fmt,
            end_date_fmt
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取财务审计意见统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest/{ts_code}")
async def get_latest_audit(ts_code: str):
    """
    获取指定股票的最新审计意见

    Args:
        ts_code: 股票代码

    Returns:
        最新审计意见
    """
    try:
        service = FinaAuditService()
        result = await service.get_latest_audit(ts_code)

        if result:
            return ApiResponse.success(data=result)
        else:
            return ApiResponse.success(data=None, message="未找到数据")

    except Exception as e:
        logger.error(f"获取最新审计意见失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_fina_audit_async(
    ts_code: str = Query(..., description="股票代码，格式：TSXXXXXX.XX（必填）"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步财务审计意见数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（必填）
        ann_date: 公告日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        period: 报告期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.fina_audit_tasks import sync_fina_audit_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None
        period_formatted = period.replace('-', '') if period else None

        # 提交Celery任务（异步执行）
        celery_task = sync_fina_audit_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_fina_audit',
            display_name='财务审计意见',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted
            },
            source='fina_audit_page'
        )

        logger.info(f"财务审计意见同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交财务审计意见同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history-async")
async def sync_fina_audit_full_history_async(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD，不填则从20090101开始"),
    current_user: User = Depends(require_admin)
):
    """
    全量同步财务审计意见历史数据（逐只股票，5并发，Redis续继）
    """
    try:
        from app.tasks.fina_audit_tasks import sync_fina_audit_full_history_task

        start_date_formatted = start_date.replace('-', '') if start_date else None

        celery_task = sync_fina_audit_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_fina_audit_full_history',
            display_name='财务审计意见（全量）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted},
            source='fina_audit_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交财务审计意见全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
