"""
融资融券标的 API 端点

提供融资融券标的数据的查询、同步和统计功能
"""

from fastapi import APIRouter, Depends
from typing import Optional
from datetime import date

from app.models.api_response import ApiResponse
from app.services.margin_secs_service import MarginSecsService
from app.services import TaskHistoryHelper
from app.tasks.extended_sync_tasks import sync_margin_secs_task
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_margin_secs(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    ts_code: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = 1000
):
    """
    获取融资融券标的数据

    Args:
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 标的代码
        exchange: 交易所代码（SSE/SZSE/BSE）
        limit: 返回记录数限制

    Returns:
        融资融券标的数据列表和统计信息
    """
    service = MarginSecsService()
    result = await service.get_margin_secs_data(
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        ts_code=ts_code,
        exchange=exchange,
        limit=limit
    )
    return ApiResponse.success(data=result)


@router.get("/latest")
async def get_latest_margin_secs(exchange: Optional[str] = None):
    """
    获取最新交易日的融资融券标的数据

    Args:
        exchange: 交易所代码（可选，SSE/SZSE/BSE）

    Returns:
        最新交易日的数据
    """
    service = MarginSecsService()
    result = await service.get_latest_data(exchange=exchange)
    return ApiResponse.success(data=result)


@router.post("/sync-async")
async def sync_margin_secs_async(
    trade_date: Optional[str] = None,
    exchange: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    异步同步融资融券标的数据

    Args:
        trade_date: 交易日期（YYYYMMDD）
        exchange: 交易所代码（SSE/SZSE/BSE）
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        current_user: 当前用户

    Returns:
        任务信息
    """
    # 提交 Celery 任务
    celery_task = sync_margin_secs_task.apply_async(
        kwargs={
            'trade_date': trade_date,
            'exchange': exchange,
            'start_date': start_date,
            'end_date': end_date
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_margin_secs',
        display_name='融资融券标的（盘前更新）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date,
            'exchange': exchange,
            'start_date': start_date,
            'end_date': end_date
        },
        source='margin_secs_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="融资融券标的同步任务已提交"
    )


@router.get("/statistics")
async def get_margin_secs_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    exchange: Optional[str] = None
):
    """
    获取融资融券标的统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期
        exchange: 交易所代码（SSE/SZSE/BSE）

    Returns:
        统计信息
    """
    service = MarginSecsService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y%m%d') if start_date else None
    end_date_str = end_date.strftime('%Y%m%d') if end_date else None

    import asyncio
    statistics = await asyncio.to_thread(
        service.margin_secs_repo.get_statistics,
        start_date=start_date_str,
        end_date=end_date_str,
        exchange=exchange
    )

    return ApiResponse.success(data=statistics)
