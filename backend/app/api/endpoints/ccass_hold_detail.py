"""
中央结算系统持股明细数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.ccass_hold_detail_service import CcassHoldDetailService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_ccass_hold_detail(
    ts_code: Optional[str] = Query(None, description="股票代码（如 00960.HK）"),
    col_participant_id: Optional[str] = Query(None, description="参与者编号（如 B01777）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="返回记录数", ge=1, le=1000)
):
    """
    查询中央结算系统持股明细数据

    Args:
        ts_code: 股票代码（如 00960.HK）
        col_participant_id: 参与者编号（如 B01777）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        limit: 返回记录数

    Returns:
        中央结算系统持股明细数据列表和统计信息
    """
    try:
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        service = CcassHoldDetailService()
        result = await service.get_ccass_hold_detail_data(
            ts_code=ts_code,
            col_participant_id=col_participant_id,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询中央结算系统持股明细数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取中央结算系统持股明细数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        # 日期格式转换
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        service = CcassHoldDetailService()
        result = await service.get_ccass_hold_detail_data(
            ts_code=ts_code,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            limit=1
        )

        return ApiResponse.success(data=result.get('statistics', {}))

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(10, description="返回记录数", ge=1, le=100)
):
    """
    获取最新的中央结算系统持股明细数据

    Args:
        ts_code: 股票代码
        limit: 返回记录数

    Returns:
        最新数据
    """
    try:
        service = CcassHoldDetailService()
        result = await service.get_latest_data(
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-participants")
async def get_top_participants(
    trade_date: str = Query(..., description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(20, description="返回记录数", ge=1, le=100)
):
    """
    获取指定日期持股量排名前N的机构

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        limit: 返回记录数

    Returns:
        持股量排名列表
    """
    try:
        # 日期格式转换
        trade_date_fmt = trade_date.replace('-', '')

        service = CcassHoldDetailService()
        result = await service.get_top_participants(
            trade_date=trade_date_fmt,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取持股量排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_ccass_hold_detail_async(
    ts_code: Optional[str] = Query(None, description="股票代码（如 00960.HK）"),
    hk_code: Optional[str] = Query(None, description="港交所代码（如 95009）"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步中央结算系统持股明细数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（如 00960.HK）
        hk_code: 港交所代码（如 95009）
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.ccass_hold_detail_tasks import sync_ccass_hold_detail_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_ccass_hold_detail_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'hk_code': hk_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_ccass_hold_detail',
            display_name='中央结算系统持股明细',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'hk_code': hk_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='ccass_hold_detail_page'
        )

        logger.info(f"中央结算系统持股明细数据同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交中央结算系统持股明细数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
