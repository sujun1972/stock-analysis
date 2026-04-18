"""
涨跌停列表 API 端点
"""
import asyncio
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date, datetime, timedelta

from app.services.limit_list_service import LimitListService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_limit_list(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc/desc")
):
    """查询涨跌停列表数据（支持分页和排序）"""
    service = LimitListService()

    if trade_date:
        start_date_fmt = trade_date.strftime('%Y%m%d')
        end_date_fmt = trade_date.strftime('%Y%m%d')
    elif start_date or end_date:
        start_date_fmt = start_date.strftime('%Y%m%d') if start_date else '20200101'
        end_date_fmt = end_date.strftime('%Y%m%d') if end_date else '29991231'
    else:
        # 未传日期：先查今天，无数据则回退到最近有数据的交易日
        resolved = await service.resolve_default_trade_date()
        start_date_fmt = resolved.replace('-', '') if resolved else '20200101'
        end_date_fmt = start_date_fmt

    result = await service.get_limit_list_data(
        start_date=start_date_fmt,
        end_date=end_date_fmt,
        ts_code=ts_code,
        limit_type=limit_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    # 回填实际使用的交易日（供前端回填日期选择器）
    result['trade_date'] = f"{start_date_fmt[:4]}-{start_date_fmt[4:6]}-{start_date_fmt[6:8]}" if start_date_fmt and len(start_date_fmt) == 8 else None

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）")
):
    """获取涨跌停列表统计信息"""
    service = LimitListService()

    if trade_date:
        start_date_fmt = trade_date.strftime('%Y%m%d')
        end_date_fmt = trade_date.strftime('%Y%m%d')
    elif start_date or end_date:
        start_date_fmt = start_date.strftime('%Y%m%d') if start_date else '20200101'
        end_date_fmt = end_date.strftime('%Y%m%d') if end_date else '29991231'
    else:
        resolved = await service.resolve_default_trade_date()
        start_date_fmt = resolved.replace('-', '') if resolved else '20200101'
        end_date_fmt = start_date_fmt

    result = await service.get_limit_list_data(
        start_date=start_date_fmt,
        end_date=end_date_fmt,
        limit_type=limit_type,
        page=1,
        page_size=1
    )

    return ApiResponse.success(data={'statistics': result.get('statistics', {})})


@router.get("/latest")
@handle_api_errors
async def get_latest(
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）")
):
    """获取最新交易日的涨跌停列表数据"""
    service = LimitListService()
    result = await service.get_latest_data(limit_type=limit_type)
    return ApiResponse.success(data=result)


@router.get("/top-limit-up")
@handle_api_errors
async def get_top_limit_up(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为最新日期）"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数限制")
):
    """获取涨停股票排行榜（按连板数和涨幅排序）"""
    service = LimitListService()
    trade_date_str = trade_date.strftime('%Y%m%d') if trade_date else None
    result = await service.get_top_limit_up_stocks(
        trade_date=trade_date_str,
        limit=limit
    )
    return ApiResponse.success(data={'items': result, 'total': len(result)})


@router.post("/sync-async")
@handle_api_errors
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选）"),
    start_date: Optional[date] = Query(None, description="开始日期（可选）"),
    end_date: Optional[date] = Query(None, description="结束日期（可选）"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）"),
    current_user: User = Depends(require_admin)
):
    """异步同步涨跌停列表数据（使用 Celery）"""
    from app.tasks.limit_list_tasks import sync_limit_list_task

    trade_date_formatted = trade_date.strftime('%Y%m%d') if trade_date else None
    start_date_formatted = start_date.strftime('%Y%m%d') if start_date else None
    end_date_formatted = end_date.strftime('%Y%m%d') if end_date else None

    # 未指定任何日期时，按 sync_configs.incremental_default_days 计算回看窗口
    if not trade_date_formatted and not start_date_formatted and not end_date_formatted:
        from app.repositories.sync_config_repository import SyncConfigRepository
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'limit_list')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        end_date_formatted = datetime.now().strftime('%Y%m%d')
        start_date_formatted = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

    celery_task = sync_limit_list_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'ts_code': ts_code,
            'limit_type': limit_type
        }
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_limit_list',
        display_name='涨跌停列表',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'ts_code': ts_code,
            'limit_type': limit_type
        },
        source='limit_list_page'
    )

    if trade_date:
        date_msg = f"涨跌停列表同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    elif start_date and end_date:
        date_msg = f"涨跌停列表同步任务已提交（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "涨跌停列表同步任务已提交"

    return ApiResponse.success(data=task_data, message=date_msg)


@router.post("/sync-full-history")
@handle_api_errors
async def sync_limit_list_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYYMMDD 或 YYYY-MM-DD，不传则从最早历史开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步涨跌停列表历史数据（按月切片，支持 Redis 续继）"""
    from app.tasks.limit_list_tasks import sync_limit_list_full_history_task
    from app.repositories.sync_config_repository import SyncConfigRepository
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'limit_list')

    start_date_formatted = start_date.replace('-', '') if start_date else None

    sync_config_repo = SyncConfigRepository()
    cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'limit_list')
    if concurrency is None:
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    celery_task = sync_limit_list_full_history_task.apply_async(
        kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_limit_list_full_history',
        display_name='涨跌停列表（全量历史）',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
        source='limit_list_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
