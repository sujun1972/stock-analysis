"""
东方财富板块成分数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from loguru import logger

from app.services.dc_member_service import DcMemberService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_dc_member(
    ts_code: Optional[str] = Query(None, description="板块指数代码（如 BK1184.DC）"),
    con_code: Optional[str] = Query(None, description="成分股票代码（如 002117.SZ）"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD（优先于 start/end）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码，从 1 开始", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=1000),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc 或 desc")
):
    """
    查询东方财富板块成分数据（支持分页和后端排序）

    Args:
        ts_code: 板块指数代码（如 BK1184.DC）
        con_code: 成分股票代码（如 002117.SZ）
        trade_date: 单日交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        page: 页码
        page_size: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        东方财富板块成分数据列表
    """
    service = DcMemberService()
    result = await service.get_dc_member_data(
        ts_code=ts_code,
        con_code=con_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="板块代码")
):
    """
    获取东方财富板块成分数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        trade_date: 单日交易日期，格式：YYYY-MM-DD
        ts_code: 板块代码

    Returns:
        统计信息
    """
    service = DcMemberService()
    stats = await service.get_statistics(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        trade_date=trade_date
    )

    return ApiResponse.success(data=stats)

@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新的东方财富板块成分数据

    Returns:
        最新数据
    """
    service = DcMemberService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)

@router.post("/sync-async")
@handle_api_errors
async def sync_dc_member_async(
    ts_code: Optional[str] = Query(None, description="板块指数代码（如 BK1184.DC）"),
    con_code: Optional[str] = Query(None, description="成分股票代码（如 002117.SZ）"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步东方财富板块成分数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 板块指数代码（如 BK1184.DC）
        con_code: 成分股票代码（如 002117.SZ）
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.dc_member_tasks import sync_dc_member_task

    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 未指定任何日期时，使用最新交易日（dc_member 每日约 5000+ 行，不使用日期范围）
    if not trade_date_formatted and not start_date_formatted and not end_date_formatted:
        from app.repositories.trading_calendar_repository import TradingCalendarRepository
        latest_day = await asyncio.to_thread(TradingCalendarRepository().get_latest_trading_day)
        trade_date_formatted = latest_day

    # 提交Celery任务（异步执行）
    celery_task = sync_dc_member_task.apply_async(
        kwargs={
            'ts_code': ts_code,
            'con_code': con_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_dc_member',
        display_name='东方财富板块成分',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'ts_code': ts_code,
            'con_code': con_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        },
        source='dc_member_page'
    )

    logger.info(f"东方财富板块成分同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_dc_member_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步东方财富板块成分历史数据（按月切片，支持 Redis 续继）"""
    from app.tasks.dc_member_tasks import sync_dc_member_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'dc_member')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'dc_member')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_dc_member_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_dc_member_full_history',
        display_name='东方财富板块成分（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='dc_member_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")