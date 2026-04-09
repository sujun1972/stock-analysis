"""
融资融券标的 API 端点

提供融资融券标的数据的查询、同步和统计功能
"""

import asyncio
from fastapi import APIRouter, Depends, Query
from typing import Optional

from app.models.api_response import ApiResponse
from app.services.margin_secs_service import MarginSecsService
from app.services import TaskHistoryHelper
from app.tasks.extended_sync_tasks import sync_margin_secs_task
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_margin_secs(
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    exchange: Optional[str] = None,
    page: int = 1,
    page_size: int = 100
):
    """
    获取融资融券标的数据（单日筛选 + 分页）

    Args:
        trade_date: 交易日期（YYYY-MM-DD），为空时自动解析最近有数据的交易日
        ts_code: 标的代码（模糊匹配）
        exchange: 交易所代码（SSE/SZSE/BSE）
        page: 页码（从1开始）
        page_size: 每页记录数

    Returns:
        融资融券标的数据列表、统计信息、总数和回填日期
    """
    service = MarginSecsService()
    result = await service.get_margin_secs_data(
        trade_date=trade_date,
        ts_code=ts_code,
        exchange=exchange,
        page=page,
        page_size=page_size
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
    trade_date: Optional[str] = None,
    exchange: Optional[str] = None
):
    """
    获取融资融券标的统计信息

    Args:
        trade_date: 交易日期（YYYY-MM-DD 或 YYYYMMDD）
        exchange: 交易所代码（SSE/SZSE/BSE）

    Returns:
        统计信息
    """
    import asyncio
    from app.repositories import MarginSecsRepository

    repo = MarginSecsRepository()
    trade_date_fmt = trade_date.replace('-', '') if trade_date else None

    statistics = await asyncio.to_thread(
        repo.get_statistics,
        start_date=trade_date_fmt,
        end_date=trade_date_fmt,
        exchange=exchange
    )

    return ApiResponse.success(data=statistics)


@router.post("/sync-full-history")
async def sync_margin_secs_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步融资融券标的历史数据（按月切片，支持 Redis 续继）"""
    try:
        from app.tasks.extended_sync_tasks import sync_margin_secs_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'margin_secs')

        start_date_formatted = start_date.replace('-', '') if start_date else None

        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'margin_secs')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_margin_secs_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_margin_secs_full_history',
            display_name='融资融券标的（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
            source='margin_secs_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        from fastapi import HTTPException
        from loguru import logger
        logger.error(f"提交融资融券标的全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
