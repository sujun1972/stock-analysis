"""
股票回购数据API端点
"""

import asyncio
import json
from typing import Optional
from datetime import date
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.repurchase_service import RepurchaseService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.get("")
async def get_repurchase(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH"),
    proc: Optional[str] = Query(None, description="回购进度，如：完成、实施、股东大会通过"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    查询股票回购数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        proc: 回购进度（可选）
        limit: 返回记录数限制

    Returns:
        回购数据列表
    """
    try:
        service = RepurchaseService()
        result = await service.get_repurchase_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            proc=proc,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询回购数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH")
):
    """
    获取回购统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）

    Returns:
        统计信息
    """
    try:
        service = RepurchaseService()
        statistics = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )
        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取回购统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码，如：600000.SH")
):
    """
    获取最新回购数据

    Args:
        ts_code: 股票代码（可选）

    Returns:
        最新回购记录
    """
    try:
        service = RepurchaseService()
        latest = await service.get_latest_data(ts_code=ts_code)
        return ApiResponse.success(data=latest)

    except Exception as e:
        logger.error(f"获取最新回购数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_repurchase_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD，不传则从2009年开始"),
    current_user: User = Depends(require_admin)
):
    """按年切片全量同步股票回购历史数据（支持中断续继）"""
    try:
        from app.tasks.repurchase_tasks import sync_repurchase_full_history_task

        start_date_formatted = start_date.replace('-', '') if start_date else None

        celery_task = sync_repurchase_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_repurchase_full_history',
            display_name='股票回购（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted},
            source='repurchase_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")
    except Exception as e:
        logger.error(f"提交股票回购全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_repurchase_async(
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步股票回购数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ann_date: 公告日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.repurchase_tasks import sync_repurchase_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_repurchase_task.apply_async(
            kwargs={
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_repurchase',
            display_name='股票回购数据',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='repurchase_page'
        )

        logger.info(f"股票回购同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交股票回购同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
