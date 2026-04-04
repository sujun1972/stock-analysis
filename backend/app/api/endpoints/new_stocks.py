"""
新股列表 API（new_stocks 表）
对应 Tushare new_share 接口
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.new_stock_service import NewStockService

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_new_stocks(
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
):
    """查询新股列表"""
    service = NewStockService()
    result = await service.get_data(
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_new_stocks_statistics(
    current_user: User = Depends(require_admin),
):
    """获取统计信息（总数、最近 7/30/90 天）"""
    service = NewStockService()
    result = await service.get_statistics()
    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_new_stocks_async(
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD，全量同步时传入"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD，留空则同步到今天"),
    days: Optional[int] = Query(None, description="最近N天（start_date 未指定时使用，默认90）"),
    current_user: User = Depends(require_admin),
):
    """
    异步同步新股列表（提交 Celery 任务）

    - **start_date**: 全量同步时传入最早历史日期（YYYYMMDD），优先于 days
    - **days**: 最近N天，默认90天
    """
    from app.tasks.sync_tasks import sync_new_stocks_task
    from app.services import TaskHistoryHelper

    effective_days = days or 90

    celery_task = sync_new_stocks_task.apply_async(
        kwargs={
            "days": effective_days,
            "start_date": start_date,
            "end_date": end_date,
        }
    )

    if start_date:
        display_name = f"新股列表同步（{start_date} ~ {end_date or '今天'}）"
    else:
        display_name = f"新股列表同步（最近{effective_days}天）"

    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name="sync.new_stocks",
        display_name=display_name,
        task_type="data_sync",
        user_id=current_user.id,
        task_params={"days": effective_days, "start_date": start_date, "end_date": end_date},
        source="new_stocks_page",
    )

    return ApiResponse.success(data=task_data, message="新股列表同步任务已提交")
