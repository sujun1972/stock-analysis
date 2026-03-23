"""
神奇九转指标数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.stk_nineturn_service import StkNineturnService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_stk_nineturn(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    freq: str = Query('daily', description="频率（daily）"),
    limit: int = Query(30, description="返回记录数", ge=1, le=10000)
):
    """
    查询神奇九转指标数据

    Args:
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        freq: 频率，默认daily
        limit: 返回记录数

    Returns:
        神奇九转指标数据列表和统计信息
    """
    try:
        service = StkNineturnService()
        result = await service.get_stk_nineturn_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询神奇九转指标数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    freq: str = Query('daily', description="频率（daily）")
):
    """
    获取神奇九转指标统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        freq: 频率，默认daily

    Returns:
        统计信息
    """
    try:
        service = StkNineturnService()
        result = await service.get_stk_nineturn_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            freq=freq,
            limit=1
        )

        return ApiResponse.success(data=result.get('statistics', {}))

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新交易日期

    Args:
        ts_code: 股票代码（可选）

    Returns:
        最新交易日期
    """
    try:
        service = StkNineturnService()
        latest_date = await service.get_latest_date(ts_code=ts_code)

        return ApiResponse.success(data={'latest_date': latest_date})

    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_turn_signals(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    signal_type: str = Query('all', description="信号类型（up:上九转, down:下九转, all:全部）"),
    limit: int = Query(50, description="返回记录数", ge=1, le=1000)
):
    """
    获取九转信号（+9或-9）

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        signal_type: 信号类型 ('up': 上九转, 'down': 下九转, 'all': 全部)
        limit: 返回记录数

    Returns:
        九转信号列表
    """
    try:
        service = StkNineturnService()
        signals = await service.get_turn_signals(
            start_date=start_date,
            end_date=end_date,
            signal_type=signal_type,
            limit=limit
        )

        return ApiResponse.success(data={'items': signals, 'total': len(signals)})

    except Exception as e:
        logger.error(f"获取九转信号失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_nineturn_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    freq: str = Query('daily', description="频率（daily）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步神奇九转指标数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    注意：
    - 所有参数均为可选，不传参数时将同步最近30天数据
    - 权限要求：6000积分
    - 单次限制：最大返回10000行数据
    - 数据起始：20230101

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期，格式：YYYY-MM-DD（可选）
        freq: 频率，默认daily
        start_date: 开始日期，格式：YYYY-MM-DD（可选）
        end_date: 结束日期，格式：YYYY-MM-DD（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_nineturn_tasks import sync_stk_nineturn_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_stk_nineturn_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'freq': freq,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_nineturn',
            display_name='神奇九转指标',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'freq': freq,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='stk_nineturn_page'
        )

        logger.info(f"神奇九转指标同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交神奇九转指标同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
