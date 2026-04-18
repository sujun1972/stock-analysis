"""
最强板块统计 API 端点
"""
import asyncio
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date, datetime, timedelta

from app.services.limit_cpt_service import LimitCptService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_limit_cpt(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    ts_code: Optional[str] = Query(None, description="板块代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('asc', description="排序方向：asc/desc")
):
    """
    查询最强板块统计数据（支持分页）

    Args:
        trade_date: 交易日期（单日查询，不传则自动取最近有数据的交易日）
        ts_code: 板块代码
        page: 页码
        page_size: 每页记录数
        sort_by: 排序字段（up_nums/cons_nums/pct_chg/days/rank）
        sort_order: 排序方向（asc/desc）

    Returns:
        最强板块统计数据列表
    """
    service = LimitCptService()

    if trade_date:
        date_str = trade_date.strftime('%Y%m%d')
        resolved_date = trade_date.strftime('%Y-%m-%d')
    else:
        # 未传日期：自动解析最近有数据的交易日（YYYY-MM-DD格式）
        resolved_date = await service.resolve_default_trade_date()
        if resolved_date:
            date_str = resolved_date.replace('-', '')
        else:
            date_str = None

    offset = (page - 1) * page_size

    result = await service.get_limit_cpt_data(
        start_date=date_str,
        end_date=date_str,
        ts_code=ts_code,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )
    result['trade_date'] = resolved_date

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    获取最强板块统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计信息
    """
    service = LimitCptService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    result = await service.get_statistics(
        start_date=start_date_str,
        end_date=end_date_str
    )

    return ApiResponse.success(data=result)


@router.get("/latest")
@handle_api_errors
async def get_latest():
    """
    获取最新交易日的最强板块统计数据

    Returns:
        最新最强板块统计数据
    """
    service = LimitCptService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)


@router.get("/top-rank")
@handle_api_errors
async def get_top_rank(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数")
):
    """
    获取涨停家数排名TOP数据

    Args:
        trade_date: 交易日期
        limit: 返回记录数

    Returns:
        排名TOP数据列表
    """
    service = LimitCptService()

    # 日期格式转换
    trade_date_str = trade_date.strftime('%Y-%m-%d') if trade_date else None

    result = await service.get_top_by_up_nums(
        trade_date=trade_date_str,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为今天）"),
    ts_code: Optional[str] = Query(None, description="板块代码"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步最强板块统计数据（使用 Celery）

    Args:
        trade_date: 交易日期（可选，默认为今天）
        ts_code: 板块代码（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        current_user: 当前用户（需要管理员权限）

    Returns:
        任务提交结果
    """
    from app.tasks.limit_cpt_tasks import sync_limit_cpt_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    trade_date_formatted = trade_date.strftime('%Y%m%d') if trade_date else None
    start_date_formatted = start_date.strftime('%Y%m%d') if start_date else None
    end_date_formatted = end_date.strftime('%Y%m%d') if end_date else None

    # 未指定任何日期时，按 sync_configs.incremental_default_days 计算回看窗口
    if not trade_date_formatted and not start_date_formatted and not end_date_formatted:
        from app.repositories.sync_config_repository import SyncConfigRepository
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'limit_cpt')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        end_date_formatted = datetime.now().strftime('%Y%m%d')
        start_date_formatted = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

    # 提交 Celery 任务
    celery_task = sync_limit_cpt_task.apply_async(
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
        task_name='tasks.sync_limit_cpt',
        display_name='最强板块统计',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        },
        source='limit_cpt_page'
    )

    # 构造提示消息
    if trade_date:
        date_msg = f"最强板块统计同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    elif start_date and end_date:
        date_msg = f"最强板块统计同步任务已提交（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "最强板块统计同步任务已提交"

    return ApiResponse.success(
        data=task_data,
        message=date_msg
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_limit_cpt_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步最强板块统计历史数据（按月切片，支持 Redis 续继）"""
    from app.tasks.limit_cpt_tasks import sync_limit_cpt_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'limit_cpt')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'limit_cpt')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_limit_cpt_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_limit_cpt_full_history',
        display_name='最强板块统计（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='limit_cpt_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
