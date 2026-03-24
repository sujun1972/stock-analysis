"""
沪深股通十大成交股 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.hsgt_top10_service import HsgtTop10Service
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_hsgt_top10(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    market_type: Optional[str] = Query(None, description="市场类型 1:沪市 3:深市"),
    limit: int = Query(30, description="返回记录数限制")
):
    """
    查询沪深股通十大成交股数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        market_type: 市场类型 1:沪市 3:深市
        limit: 返回记录数限制

    Returns:
        沪深股通十大成交股数据列表
    """
    try:
        service = HsgtTop10Service()
        result = await service.get_hsgt_top10_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            market_type=market_type,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"查询沪深股通十大成交股数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    market_type: Optional[str] = Query(None, description="市场类型 1:沪市 3:深市")
):
    """
    获取沪深股通十大成交股统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        market_type: 市场类型

    Returns:
        统计信息
    """
    try:
        service = HsgtTop10Service()
        result = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    market_type: Optional[str] = Query(None, description="市场类型 1:沪市 3:深市"),
    limit: int = Query(10, description="返回记录数限制")
):
    """
    获取最新沪深股通十大成交股数据

    Args:
        market_type: 市场类型
        limit: 返回记录数限制

    Returns:
        最新数据
    """
    try:
        service = HsgtTop10Service()
        result = await service.get_latest_data(
            market_type=market_type,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_by_net_amount(
    trade_date: str = Query(..., description="交易日期，格式：YYYY-MM-DD"),
    market_type: Optional[str] = Query(None, description="市场类型 1:沪市 3:深市"),
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取指定日期净成交金额排名前N的股票

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD
        market_type: 市场类型
        limit: 返回记录数限制

    Returns:
        排名数据
    """
    try:
        service = HsgtTop10Service()
        result = await service.get_top_by_net_amount(
            trade_date=trade_date,
            market_type=market_type,
            limit=limit
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取排名数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_hsgt_top10_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    market_type: Optional[str] = Query(None, description="市场类型 1:沪市 3:深市"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步沪深股通十大成交股数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        market_type: 市场类型 1:沪市 3:深市（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.hsgt_top10_tasks import sync_hsgt_top10_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_hsgt_top10_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'market_type': market_type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_hsgt_top10',
            display_name='沪深股通十大成交股',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'market_type': market_type
            },
            source='hsgt_top10_page'
        )

        logger.info(f"沪深股通十大成交股同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交沪深股通十大成交股同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
