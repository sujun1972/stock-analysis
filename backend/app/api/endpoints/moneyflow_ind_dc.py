"""板块资金流向API（东财概念及行业板块资金流向 DC）"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.services.moneyflow_ind_dc_service import MoneyflowIndDcService

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_moneyflow_ind_dc(
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD（优先于 start/end_date）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="数据类型(行业、概念、地域)"),
    ts_code: Optional[str] = Query(None, description="板块代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向 asc/desc"),
    # 旧参数保留向后兼容
    limit: Optional[int] = Query(None, ge=1, le=500, description="[已废弃] 返回记录数，请改用 page/page_size"),
    offset: int = Query(0, ge=0, description="[已废弃] 偏移量，请改用 page/page_size"),
    current_user: User = Depends(get_current_user)
):
    """获取板块资金流向数据"""
    service = MoneyflowIndDcService()

    # 未指定任何日期时，自动解析最近有数据的交易日
    resolved_trade_date = trade_date
    if not trade_date and not start_date and not end_date:
        resolved_trade_date = await service.resolve_default_trade_date(content_type=content_type)

    result = await asyncio.to_thread(
        service.get_moneyflow_data,
        trade_date=resolved_trade_date,
        start_date=start_date,
        end_date=end_date,
        content_type=content_type,
        ts_code=ts_code,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )
    return ApiResponse.success(data=result, message="获取板块资金流向成功")

@router.post("/sync")
@handle_api_errors
async def sync_moneyflow_ind_dc(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="资金类型(行业、概念、地域)"),
    current_user: User = Depends(require_admin)
):
    """同步板块资金流向数据（管理员功能）"""
    from app.services.extended_sync_service import ExtendedDataSyncService
    service = ExtendedDataSyncService()
    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    result = await service.sync_moneyflow_ind_dc(
        ts_code=None,
        trade_date=trade_date_formatted,
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        content_type=content_type
    )

    if result["status"] == "success":
        return ApiResponse.success(data=result, message=f"成功同步 {result['records']} 条板块资金流向数据")
    else:
        return ApiResponse.error(message=result.get("error", "同步失败"))

@router.post("/sync-async")
@handle_api_errors
async def sync_moneyflow_ind_dc_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="资金类型(行业、概念、地域)"),
    current_user: User = Depends(require_admin)
):
    """异步同步板块资金流向数据"""
    from app.tasks.moneyflow_ind_dc_tasks import sync_moneyflow_ind_dc_task
    from app.services import TaskHistoryHelper

    trade_date_formatted = trade_date.replace('-', '') if trade_date else None
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    celery_task = sync_moneyflow_ind_dc_task.apply_async(
        kwargs={
            'ts_code': None,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'content_type': content_type
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_moneyflow_ind_dc',
        display_name='板块资金流向',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'content_type': content_type
        },
        source='moneyflow_ind_dc_page'
    )

    logger.info(f"板块资金流向同步任务已提交: {celery_task.id}")
    return ApiResponse.success(
        data=task_data,
        message="任务已提交，正在后台执行"
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_moneyflow_ind_dc_full_history_async(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD，默认 2015-01-01"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量同步板块资金流向历史数据（按窗口切片 × 三板块类型，支持中断续继）

    行业/地域用 7 天窗口，概念用 1 天窗口；Redis Set 记录已完成片段，支持中断后续继。
    积分消耗较高（6000积分/次 × 三类型），建议仅在初次建库或需要补全历史数据时使用。
    """
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'moneyflow_ind_dc')
    from app.tasks.moneyflow_ind_dc_tasks import sync_moneyflow_ind_dc_full_history_task
    from app.services import TaskHistoryHelper
    from app.repositories.sync_config_repository import SyncConfigRepository

    start_date_formatted = start_date.replace('-', '') if start_date else None

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'moneyflow_ind_dc')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_moneyflow_ind_dc_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_moneyflow_ind_dc_full_history',
        display_name='板块资金流向（DC）全量历史同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='moneyflow_ind_dc_page'
    )

    logger.info(f"板块资金流向（DC）全量历史同步任务已提交: {celery_task.id}")
    return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

@router.get("/latest")
@handle_api_errors
async def get_latest_moneyflow_ind_dc(
    content_type: Optional[str] = Query(None, description="数据类型(行业、概念、地域)"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user)
):
    """获取最新的板块资金流向数据"""
    service = MoneyflowIndDcService()
    data = await asyncio.to_thread(service.get_latest_moneyflow, content_type=content_type, limit=limit)
    if not data:
        return ApiResponse.success(data=[], message="暂无板块资金流向数据")
    return ApiResponse.success(data=data, message="获取最新板块资金流向成功")

@router.get("/top")
@handle_api_errors
async def get_top_moneyflow_ind_dc(
    content_type: Optional[str] = Query(None, description="数据类型(行业、概念、地域)"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user)
):
    """获取最新交易日 TOP N 板块资金流向数据（供图表使用）"""
    service = MoneyflowIndDcService()
    data = await asyncio.to_thread(service.get_latest_moneyflow, content_type=content_type, limit=limit)
    if not data:
        return ApiResponse.success(data=[], message="暂无板块资金流向数据")
    return ApiResponse.success(data=data, message="获取TOP板块资金流向成功")