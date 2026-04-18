"""
东方财富板块数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.dc_index_service import DcIndexService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_dc_index(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD，为空时自动解析最近有数据的交易日"),
    idx_type: Optional[str] = Query(None, description="板块类型（概念板块/行业板块/地域板块）"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=500),
    sort_by: Optional[str] = Query(None, description="排序字段（pct_change/leading_pct/turnover_rate/total_mv/up_num/down_num）"),
    sort_order: Optional[str] = Query(None, description="排序方向（asc/desc）"),
):
    """
    查询东方财富板块数据（单日分页模式）

    Returns:
        东方财富板块数据列表
    """
    service = DcIndexService()
    result = await service.get_dc_index_data(
        trade_date=trade_date,
        idx_type=idx_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    idx_type: Optional[str] = Query(None, description="板块类型（概念板块/行业板块/地域板块）"),
):
    """
    获取东方财富板块数据统计信息（按单日或全量汇总）

    Returns:
        统计信息
    """
    service = DcIndexService()
    # trade_date 转为同一天的 start/end 范围查询
    date_fmt = trade_date.replace('-', '') if trade_date else None
    stats = await service.get_statistics(
        start_date=date_fmt,
        end_date=date_fmt,
        idx_type=idx_type
    )

    return ApiResponse.success(data=stats)

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新的东方财富板块数据

    Returns:
        最新数据
    """
    service = DcIndexService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)

@router.post("/sync-async")
@handle_api_errors
async def sync_dc_index_async(
    ts_code: Optional[str] = Query(None, description="板块代码"),
    name: Optional[str] = Query(None, description="板块名称"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    idx_type: str = Query('概念板块', description="板块类型（概念板块/行业板块/地域板块）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步东方财富板块数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 板块代码
        name: 板块名称
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        idx_type: 板块类型（必填，默认：概念板块）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.dc_index_tasks import sync_dc_index_task

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 未指定任何日期时，使用最新交易日（dc_index 每日约 5000+ 行，不使用日期范围）
    if not trade_date_formatted and not start_date_formatted and not end_date_formatted:
        from app.repositories.trading_calendar_repository import TradingCalendarRepository
        latest_day = await asyncio.to_thread(TradingCalendarRepository().get_latest_trading_day)
        trade_date_formatted = latest_day

    celery_task = sync_dc_index_task.apply_async(
        kwargs={
            'ts_code': ts_code,
            'name': name,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'idx_type': idx_type
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_dc_index',
        display_name='东方财富板块数据',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code,
            'name': name,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'idx_type': idx_type
        },
        source='dc_index_page'
    )

    logger.info(f"东方财富板块数据同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_dc_index_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    idx_type: str = Query('概念板块', description="板块类型（概念板块/行业板块/地域板块）"),
    current_user: User = Depends(require_admin)
):
    """全量同步东方财富板块数据历史（按月切片，支持 Redis 续继）"""
    from app.tasks.dc_index_tasks import sync_dc_index_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'dc_index')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'dc_index')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 3) if cfg else 3

    celery_task = sync_dc_index_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency, 'idx_type': idx_type}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_dc_index_full_history',
        display_name=f'东方财富板块数据（全量历史·{idx_type}）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency, 'idx_type': idx_type},
        source='dc_index_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")