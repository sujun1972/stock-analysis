"""
财报披露计划 API 端点

增量同步：从 sync_configs 读取任务名，动态分发
全量同步：独立端点 /sync-full-history
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends
from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.disclosure_date_service import DisclosureDateService
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_disclosure_date(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    start_date: Optional[str] = Query(None, description="报告期开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="报告期结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="限制返回数量，默认30"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """查询财报披露计划数据"""
    # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    service = DisclosureDateService()
    result = await service.get_disclosure_date_data(
        ts_code=ts_code,
        start_date=start_date_formatted,
        end_date=end_date_formatted,
        limit=limit,
        offset=offset
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="报告期开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="报告期结束日期，格式：YYYY-MM-DD")
):
    """获取财报披露计划统计信息"""
    # 日期格式转换
    start_date_formatted = start_date.replace('-', '') if start_date else None
    end_date_formatted = end_date.replace('-', '') if end_date else None

    from app.repositories.disclosure_date_repository import DisclosureDateRepository
    repo = DisclosureDateRepository()

    statistics = await asyncio.to_thread(
        repo.get_statistics,
        start_date_formatted,
        end_date_formatted
    )

    return ApiResponse.success(data=statistics)


@router.get("/latest")
@handle_api_errors
async def get_latest_disclosure_date(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, description="限制返回数量")
):
    """获取最新财报披露计划数据（按报告期排序）"""
    service = DisclosureDateService()
    result = await service.get_disclosure_date_data(
        ts_code=ts_code,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_disclosure_date_async(
    current_user: User = Depends(require_admin)
):
    """
    增量同步财报披露计划数据（通过Celery任务）

    从 sync_configs 读取 incremental_task_name，动态分发任务。
    不传日期参数，由 Service 层的 sync_incremental() 自动计算。
    """
    from app.api.sync_utils import dispatch_incremental_sync
    return await dispatch_incremental_sync(
        table_key='disclosure_date',
        display_name='财报披露计划增量同步',
        fallback_task_name='tasks.sync_disclosure_date',
        user_id=current_user.id,
        source='disclosure_date_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_disclosure_date_full_history_async(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """触发全量历史财报披露计划同步（可中断续继）"""
    from app.api.sync_utils import dispatch_full_history_sync
    return await dispatch_full_history_sync(
        table_key='disclosure_date',
        display_name='财报披露计划全量同步',
        task_name='tasks.sync_disclosure_date_full_history',
        user_id=current_user.id,
        source='disclosure_date_page',
        concurrency=concurrency,
        default_concurrency=5,
    )
