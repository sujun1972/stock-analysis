"""宏观经济指标 API 端点（前缀 /macro-indicators，Phase 3 of news_anns roadmap）。

数据源：AkShare 免费宏观接口（替代 Tushare eco_cal）。

查询类：分页列表 / 按 indicator_code 取序列 / 最近快照（CIO 用）。
同步类：增量（遍历所有 indicator fetcher，整体 UPSERT） / 全量（AkShare 无历史参数，等价于增量）。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.error_handler import handle_api_errors
from app.api.sync_utils import dispatch_full_history_sync, dispatch_incremental_sync
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.models.user import User

router = APIRouter()


# ------------------------------------------------------------------
# 查询
# ------------------------------------------------------------------

@router.get("")
@handle_api_errors
async def list_indicators(
    indicator_code: Optional[str] = Query(None, description="指标代码（cpi_yoy / pmi_manu / shibor_on 等）"),
    start_date: Optional[date] = Query(None, description="报告期起始"),
    end_date: Optional[date] = Query(None, description="报告期结束"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    sort_by: Optional[str] = Query(None, description="排序字段：period_date / publish_date / indicator_code"),
    sort_order: str = Query('desc'),
):
    """分页查询宏观经济指标（跨指标，默认按 period_date 倒序）。"""
    from app.services.news_anns import MacroSyncService
    svc = MacroSyncService()
    start_fmt = start_date.strftime('%Y-%m-%d') if start_date else None
    end_fmt = end_date.strftime('%Y-%m-%d') if end_date else None
    result = await svc.list_indicators(
        indicator_code=indicator_code,
        start_date=start_fmt, end_date=end_fmt,
        page=page, page_size=page_size,
        sort_by=sort_by, sort_order=sort_order,
    )
    return ApiResponse.success(data=result)


@router.get("/series/{indicator_code}")
@handle_api_errors
async def get_series(
    indicator_code: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(60, ge=1, le=500),
):
    """按单个 indicator_code 取时间序列（period_date 倒序）。"""
    from app.services.news_anns import MacroSyncService
    svc = MacroSyncService()
    start_fmt = start_date.strftime('%Y-%m-%d') if start_date else None
    end_fmt = end_date.strftime('%Y-%m-%d') if end_date else None
    items = await svc.get_series(indicator_code, start_fmt, end_fmt, int(limit))
    return ApiResponse.success(data={
        'indicator_code': indicator_code,
        'items': items,
        'total': len(items),
    })


@router.get("/snapshot")
@handle_api_errors
async def get_snapshot(lookback_months: int = Query(12, ge=1, le=60)):
    """宏观快照：各指标最新值 + 最近 N 个月序列（供宏观专家 / CIO 调用）。"""
    from app.services.news_anns import MacroSyncService
    svc = MacroSyncService()
    snapshot = await svc.get_macro_snapshot(int(lookback_months))
    return ApiResponse.success(data=snapshot)


# ------------------------------------------------------------------
# 同步
# ------------------------------------------------------------------

@router.post("/sync-async")
@handle_api_errors
async def sync_async(current_user: User = Depends(require_admin)):
    """增量同步（遍历全部 indicator，拉完整历史并 UPSERT）。"""
    return await dispatch_incremental_sync(
        table_key='macro_indicators',
        display_name='宏观经济指标增量同步',
        fallback_task_name='tasks.sync_macro_indicators',
        user_id=current_user.id,
        source='macro_indicators_page',
    )


@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=5),
    current_user: User = Depends(require_admin),
):
    """全量历史同步（AkShare 宏观接口无日期参数，等价于单次增量）。"""
    return await dispatch_full_history_sync(
        table_key='macro_indicators',
        display_name='宏观经济指标全量同步',
        task_name='tasks.sync_macro_indicators_full_history',
        user_id=current_user.id,
        source='macro_indicators_page',
        concurrency=concurrency,
        default_concurrency=1,
    )
