"""
财务指标数据 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.fina_indicator_service import FinaIndicatorService
from app.models.api_response import ApiResponse
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_fina_indicator(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD（如2023-12-31表示年报）"),
    limit: int = Query(30, description="限制返回数量，默认30"),
    offset: int = Query(0, description="偏移量（用于分页）")
):
    """查询财务指标数据"""
    # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None
    period_formatted = period.replace('-', '') if period else None

    service = FinaIndicatorService()
    result = await service.get_fina_indicator_data(
        ts_code=ts_code,
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        period=period_formatted,
        limit=limit,
        offset=offset
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """获取财务指标统计信息"""
    # 日期格式转换
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    service = FinaIndicatorService()
    statistics = await service.get_statistics(
        ts_code=ts_code,
        start_date=start_date_formatted,
        end_date=end_date_formatted
    )

    return ApiResponse.success(data=statistics)


@router.get("/latest")
@handle_api_errors
async def get_latest_fina_indicator(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, description="限制返回数量")
):
    """获取最新财务指标数据（按公告日期排序）"""
    service = FinaIndicatorService()
    result = await service.get_fina_indicator_data(
        ts_code=ts_code,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_fina_indicator_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步财务指标数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.repositories.sync_config_repository import SyncConfigRepository

    cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'fina_indicator')
    task_name = (cfg.get('incremental_task_name') or 'tasks.sync_fina_indicator') if cfg else 'tasks.sync_fina_indicator'

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(task_name)

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name=task_name,
        display_name='财务指标增量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={},
        source='fina_indicator_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="增量同步任务已提交，正在后台执行"
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_fina_indicator_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史财务指标同步（可中断续继）"""
    from app.api.endpoints.sync_dashboard import release_stale_lock
    await asyncio.to_thread(release_stale_lock, 'fina_indicator')
    from app.repositories.sync_config_repository import SyncConfigRepository

    if concurrency is None:
        sync_config_repo = SyncConfigRepository()
        cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'fina_indicator')
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

    from app.celery_app import celery_app
    celery_task = celery_app.send_task(
        'tasks.sync_fina_indicator_full_history',
        kwargs={'concurrency': concurrency}
    )

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_fina_indicator_full_history',
        display_name='财务指标全量同步',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={'concurrency': concurrency},
        source='fina_indicator_page'
    )

    return ApiResponse.success(data=task_data, message="全量同步任务已提交")
