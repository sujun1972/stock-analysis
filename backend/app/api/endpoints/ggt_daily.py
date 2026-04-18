"""
港股通每日成交统计 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.ggt_daily_service import GgtDailyService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_ggt_daily(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="每页记录数"),
    offset: int = Query(0, description="分页偏移量")
):
    """
    查询港股通每日成交统计数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        limit: 每页记录数
        offset: 分页偏移量

    Returns:
        港股通每日成交统计数据列表
    """
    service = GgtDailyService()
    result = await service.get_data(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取港股通每日成交统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    service = GgtDailyService()
    # 转换日期格式
    start_date_fmt = start_date.replace('-', '') if start_date else None
    end_date_fmt = end_date.replace('-', '') if end_date else None

    # 获取统计信息
    result = await asyncio.to_thread(
        service.ggt_daily_repo.get_statistics,
        start_date=start_date_fmt,
        end_date=end_date_fmt
    )
    return ApiResponse.success(data=result)

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新港股通每日成交统计数据

    Returns:
        最新数据
    """
    service = GgtDailyService()
    result = await service.get_latest_data()
    return ApiResponse.success(data=result)

@router.post("/sync-async")
@handle_api_errors
async def sync_ggt_daily_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD，支持多日逗号分隔"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步港股通每日成交统计数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD，支持多日逗号分隔（如：2024-03-01,2024-03-02）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.ggt_daily_tasks import sync_ggt_daily_task

    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 提交Celery任务（异步执行）
    celery_task = sync_ggt_daily_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_ggt_daily',
        display_name='港股通每日成交统计',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        },
        source='ggt_daily_page'
    )

    logger.info(f"港股通每日成交统计同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_ggt_daily_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD，不传则从2014年开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步港股通每日成交统计历史数据（按年切片 + Redis 续继）"""
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'ggt_daily')
    from app.tasks.ggt_daily_tasks import sync_ggt_daily_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    # 未传并发数时，从 sync_configs 读取，兜底默认值
    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'ggt_daily')
        concurrency = (cfg.get('full_sync_concurrency') or 3) if cfg else 3

    start_date_fmt = start_date.replace('-', '') if start_date else None

    celery_task = sync_ggt_daily_full_history_task.apply_async(
        kwargs={'start_date': start_date_fmt, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_ggt_daily_full_history',
        display_name='港股通每日成交统计（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_fmt, 'concurrency': concurrency},
        source='ggt_daily_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
