"""
财报披露计划 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.core.dependencies import require_admin, get_current_user
from app.models.user import User
from app.services.disclosure_date_service import DisclosureDateService
from app.models.api_response import ApiResponse
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_disclosure_date(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    start_date: Optional[str] = Query(None, description="报告期开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="报告期结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="限制返回数量，默认30")
):
    """
    查询财报披露计划数据

    财报披露计划包括预计披露日期、实际披露日期等信息
    """
    try:
        service = DisclosureDateService()
        result = await service.get_disclosure_date_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询财报披露计划数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="报告期开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="报告期结束日期，格式：YYYY-MM-DD")
):
    """
    获取财报披露计划统计信息
    """
    try:
        # 日期格式转换
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        service = DisclosureDateService()
        from app.repositories.disclosure_date_repository import DisclosureDateRepository
        repo = DisclosureDateRepository()

        statistics = await asyncio.to_thread(
            repo.get_statistics,
            start_date_formatted,
            end_date_formatted
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取财报披露计划统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_disclosure_date(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, description="限制返回数量")
):
    """
    获取最新财报披露计划数据（按报告期排序）
    """
    try:
        service = DisclosureDateService()
        result = await service.get_disclosure_date_data(
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新财报披露计划数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_disclosure_date_async(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    end_date: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD（每个季度最后一天）"),
    pre_date: Optional[str] = Query(None, description="计划披露日期，格式：YYYY-MM-DD"),
    ann_date: Optional[str] = Query(None, description="最新披露公告日，格式：YYYY-MM-DD"),
    actual_date: Optional[str] = Query(None, description="实际披露日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步财报披露计划数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    注意：
    - 积分消耗：500分起
    - 建议按报告期查询，如查询2024年报：end_date=2024-12-31

    Args:
        ts_code: 股票代码，格式：TSXXXXXX.XX
        end_date: 报告期，格式：YYYY-MM-DD（如2024-12-31表示2024年年报）
        pre_date: 计划披露日期，格式：YYYY-MM-DD
        ann_date: 最新披露公告日，格式：YYYY-MM-DD
        actual_date: 实际披露日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.disclosure_date_tasks import sync_disclosure_date_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        end_date_formatted = end_date.replace('-', '') if end_date else None
        pre_date_formatted = pre_date.replace('-', '') if pre_date else None
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        actual_date_formatted = actual_date.replace('-', '') if actual_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_disclosure_date_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'end_date': end_date_formatted,
                'pre_date': pre_date_formatted,
                'ann_date': ann_date_formatted,
                'actual_date': actual_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_disclosure_date',
            display_name='财报披露计划',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'end_date': end_date_formatted,
                'pre_date': pre_date_formatted,
                'ann_date': ann_date_formatted,
                'actual_date': actual_date_formatted
            },
            source='disclosure_date_page'
        )

        logger.info(f"财报披露计划同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交财报披露计划同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
