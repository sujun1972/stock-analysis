"""
融资融券交易明细API端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.core.dependencies import require_admin
from app.models.user import User
from app.services.margin_detail_service import MarginDetailService
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_margin_detail(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向：asc/desc"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券交易明细数据

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD（留空则自动返回最近有数据的交易日）
        ts_code: 股票代码
        page: 页码
        page_size: 每页数量
        sort_by: 排序字段（白名单：rzrqye/rzye/rqye/rzmre/rzche/rqmcl）
        sort_order: 排序方向（asc/desc）
        current_user: 当前登录用户（管理员）

    Returns:
        融资融券交易明细数据列表，含 trade_date 供前端回填
    """
    service = MarginDetailService()
    result = await service.get_margin_detail_data(
        trade_date=trade_date,
        ts_code=ts_code,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return ApiResponse.success(data=result)

@router.get("/statistics")
@handle_api_errors
async def get_margin_detail_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券交易明细统计数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        统计数据
    """
    service = MarginDetailService()
    statistics = await service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )
    return ApiResponse.success(data=statistics)

@router.get("/top-stocks")
@handle_api_errors
async def get_top_stocks(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券余额TOP股票

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD
        limit: 返回数量
        current_user: 当前登录用户（管理员）

    Returns:
        TOP股票列表
    """
    service = MarginDetailService()
    top_stocks = await service.get_top_stocks(
        trade_date=trade_date,
        limit=limit
    )
    return ApiResponse.success(data=top_stocks)

@router.post("/sync-async")
@handle_api_errors
async def sync_margin_detail_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步融资融券交易明细数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    from app.tasks.margin_detail_tasks import sync_margin_detail_task
    from app.services import TaskHistoryHelper

    # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    # 提交Celery任务（异步执行）
    celery_task = sync_margin_detail_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_margin_detail',
        display_name='融资融券交易明细',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        },
        source='margin_detail_page'
    )

    logger.info(f"融资融券交易明细同步任务已提交: {celery_task.id}")

    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_margin_detail_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步融资融券交易明细历史数据（按月切片，支持 Redis 续继）"""
    from app.tasks.margin_detail_tasks import sync_margin_detail_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    from app.services import TaskHistoryHelper

    await asyncio.to_thread(release_stale_lock, 'margin_detail')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'margin_detail')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_margin_detail_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_margin_detail_full_history',
        display_name='融资融券交易明细（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='margin_detail_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
