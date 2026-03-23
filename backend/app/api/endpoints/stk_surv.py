"""
机构调研表 API 端点
"""

import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from loguru import logger

from app.services.stk_surv_service import StkSurvService
from app.services import TaskHistoryHelper
from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_stk_surv(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    org_type: Optional[str] = Query(None, description="接待公司类型"),
    rece_mode: Optional[str] = Query(None, description="接待方式"),
    limit: int = Query(30, description="返回记录数限制")
):
    """
    查询机构调研数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        org_type: 接待公司类型（可选）
        rece_mode: 接待方式（可选）
        limit: 返回记录数限制

    Returns:
        机构调研数据列表
    """
    try:
        service = StkSurvService()
        result = await service.get_stk_surv_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            org_type=org_type,
            rece_mode=rece_mode,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"查询机构调研数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取机构调研统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    try:
        service = StkSurvService()
        stats = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=stats)
    except Exception as e:
        logger.error(f"获取机构调研统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取最新的机构调研数据

    Args:
        limit: 返回记录数限制

    Returns:
        最新机构调研数据列表
    """
    try:
        service = StkSurvService()
        result = await service.get_latest_data(limit=limit)
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新机构调研数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_surv_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="调研日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="调研开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="调研结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步机构调研数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可选）
        trade_date: 调研日期，格式：YYYY-MM-DD（可选）
        start_date: 调研开始日期，格式：YYYY-MM-DD（可选）
        end_date: 调研结束日期，格式：YYYY-MM-DD（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_surv_tasks import sync_stk_surv_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_stk_surv_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_surv',
            display_name='机构调研表',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='stk_surv_page'
        )

        logger.info(f"机构调研数据同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交机构调研数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
