"""
限售股解禁 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.share_float_service import ShareFloatService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.get("")
@handle_api_errors
async def get_share_float(
    start_date: Optional[str] = Query(None, description="开始日期（解禁日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（解禁日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    float_date: Optional[str] = Query(None, description="解禁日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    查询限售股解禁数据

    Args:
        start_date: 开始日期（解禁日期），格式：YYYY-MM-DD
        end_date: 结束日期（解禁日期），格式：YYYY-MM-DD
        ts_code: 股票代码
        ann_date: 公告日期，格式：YYYY-MM-DD
        float_date: 解禁日期，格式：YYYY-MM-DD
        limit: 返回记录数限制

    Returns:
        限售股解禁数据列表
    """
    # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None
    ann_date_formatted = ann_date.replace('-', '') if ann_date else None
    float_date_formatted = float_date.replace('-', '') if float_date else None

    service = ShareFloatService()
    result = await service.get_share_float_data(
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        ts_code=ts_code,
        ann_date=ann_date_formatted,
        float_date=float_date_formatted,
        limit=limit,
        offset=offset
    )

    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（解禁日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（解禁日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取限售股解禁统计信息

    Args:
        start_date: 开始日期（解禁日期），格式：YYYY-MM-DD
        end_date: 结束日期（解禁日期），格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    service = ShareFloatService()
    result = await service.get_statistics(
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        ts_code=ts_code
    )

    return ApiResponse.success(data=result)

@router.get("/latest")
@handle_api_errors
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新的限售股解禁数据

    Args:
        ts_code: 股票代码

    Returns:
        最新数据
    """
    service = ShareFloatService()
    result = await service.get_latest_data(ts_code=ts_code)

    return ApiResponse.success(data=result)

@router.post("/sync-full-history")
@handle_api_errors
async def sync_share_float_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从 sync_configs 读取"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步限售股解禁历史数据（支持中断续继，切片策略从 sync_configs.full_sync_strategy 读取）"""
    from app.tasks.share_float_tasks import sync_share_float_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'share_float')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    # 从 sync_configs 读取策略、并发数、起始日期
    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'share_float')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
    strategy = (cfg.get('full_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    celery_task = sync_share_float_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency, 'strategy': strategy,
                'max_requests_per_minute': max_rpm}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_share_float_full_history',
        display_name='限售股解禁（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency, 'strategy': strategy,
                     'max_requests_per_minute': max_rpm},
        source='share_float_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")

@router.get("/suggest-start-date")
@handle_api_errors
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """
    返回增量同步的建议起始日期（YYYYMMDD）。

    计算规则：
      候选起始 = 今天 - incremental_default_days（sync_configs 中配置）
      上次结束 = sync_history 中最近一次增量成功的 data_end_date
      建议起始 = min(候选起始, 上次结束)，取更早者保证数据连续
    """
    service = ShareFloatService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
@handle_api_errors
async def sync_share_float_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    float_date: Optional[str] = Query(None, description="解禁日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="解禁开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="解禁结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步增量同步限售股解禁数据（Celery 任务）"""
    from app.tasks.share_float_tasks import sync_share_float_task
    from app.repositories.sync_config_repository import SyncConfigRepository

    ts_code_formatted = ts_code
    ann_date_formatted = ann_date.replace('-', '') if ann_date else None
    float_date_formatted = float_date.replace('-', '') if float_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 从 sync_configs 读取增量同步策略及任务限速
    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'share_float')
    sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_month') if cfg else 'by_month'
    max_rpm = cfg.get('max_requests_per_minute') if cfg else None

    # 若未指定 start_date 且策略需要日期范围，自动计算建议起始日期
    if not start_date_formatted and sync_strategy in ('by_date_range', 'by_month', 'by_week', 'by_date', 'by_ts_code'):
        from app.services.share_float_service import ShareFloatService
        suggested = await ShareFloatService().get_suggested_start_date()
        if suggested:
            start_date_formatted = suggested
            logger.info(f"限售股解禁增量同步：未传 start_date，自动使用建议起始日期 {start_date_formatted}")

    celery_task = sync_share_float_task.apply_async(
        kwargs={
            'ts_code': ts_code_formatted,
            'ann_date': ann_date_formatted,
            'float_date': float_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_share_float',
        display_name='限售股解禁',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'sync_strategy': sync_strategy,
            'max_requests_per_minute': max_rpm,
        },
        source='share_float_page'
    )

    logger.info(f"限售股解禁增量同步任务已提交: {celery_task.id} strategy={sync_strategy}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")
