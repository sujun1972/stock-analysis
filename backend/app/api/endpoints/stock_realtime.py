"""
实时行情 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.stock_realtime_service import StockRealtimeService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_realtime_quotes(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(30, ge=1, le=100, description="每页记录数，最大100")
):
    """
    查询实时行情数据（所有股票，支持分页）

    Args:
        page: 页码（从1开始）
        page_size: 每页记录数

    Returns:
        实时行情数据列表（带分页信息）
    """
    try:
        service = StockRealtimeService()
        result = await service.get_all_realtime(page=page, page_size=page_size)

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询实时行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/code/{code}")
async def get_realtime_by_code(
    code: str
):
    """
    根据股票代码查询实时行情

    Args:
        code: 股票代码

    Returns:
        实时行情数据
    """
    try:
        service = StockRealtimeService()
        result = await service.get_by_code(code=code)

        if result is None:
            raise HTTPException(status_code=404, detail=f"股票 {code} 的实时行情不存在")

        return ApiResponse.success(data=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询股票 {code} 实时行情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-gainers")
async def get_top_gainers(
    limit: int = Query(50, ge=1, le=100, description="返回记录数，最大100")
):
    """
    获取涨幅榜前N名

    Args:
        limit: 返回记录数

    Returns:
        涨幅榜数据
    """
    try:
        service = StockRealtimeService()
        result = await service.get_top_gainers(limit=limit)

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询涨幅榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-losers")
async def get_top_losers(
    limit: int = Query(50, ge=1, le=100, description="返回记录数，最大100")
):
    """
    获取跌幅榜前N名

    Args:
        limit: 返回记录数

    Returns:
        跌幅榜数据
    """
    try:
        service = StockRealtimeService()
        result = await service.get_top_losers(limit=limit)

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询跌幅榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics():
    """
    获取实时行情统计信息

    Returns:
        统计信息
    """
    try:
        service = StockRealtimeService()
        stats = await service.get_statistics()

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取实时行情统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_realtime_async(
    batch_size: Optional[int] = Query(100, description="批次大小"),
    update_oldest: bool = Query(False, description="是否优先更新最旧的数据"),
    data_source: str = Query('akshare', description="数据源（akshare 或 tushare）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步实时行情数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        batch_size: 批次大小
        update_oldest: 是否优先更新最旧的数据
        data_source: 数据源（akshare 或 tushare）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stock_realtime_tasks import sync_realtime_quotes_task

        # 提交Celery任务（异步执行）
        celery_task = sync_realtime_quotes_task.apply_async(
            kwargs={
                'codes': None,  # None表示全部
                'batch_size': batch_size,
                'update_oldest': update_oldest,
                'data_source': data_source
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_realtime_quotes',
            display_name='实时行情同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'batch_size': batch_size,
                'update_oldest': update_oldest,
                'data_source': data_source
            },
            source='realtime_page'
        )

        logger.info(f"实时行情同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交实时行情同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
