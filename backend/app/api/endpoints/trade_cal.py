"""
交易日历 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.services.trading_calendar_service import TradingCalendarService
from app.services import TaskHistoryHelper
from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_trade_calendar(
    exchange: str = Query('SSE', description="交易所代码（SSE/SZSE/CFFEX/SHFE/CZCE/DCE/INE）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    is_open: Optional[str] = Query(None, description="是否交易：'0'休市 '1'交易"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=500, description="每页记录数")
):
    """查询交易日历数据（支持分页）"""
    service = TradingCalendarService()
    result = await service.get_calendar_data(
        exchange=exchange,
        start_date=start_date,
        end_date=end_date,
        is_open=is_open,
        page=page,
        page_size=page_size
    )
    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    year: Optional[int] = Query(None, description="年份（默认当前年份）"),
    exchange: str = Query('SSE', description="交易所代码")
):
    """获取交易日历统计信息（交易日数、休市日数等）"""
    service = TradingCalendarService()
    result = await service.get_statistics(year=year, exchange=exchange)
    return ApiResponse.success(data=result)


@router.get("/latest")
@handle_api_errors
async def get_latest(
    exchange: str = Query('SSE', description="交易所代码")
):
    """获取最新交易日信息"""
    service = TradingCalendarService()
    result = await service.get_latest_info(exchange=exchange)
    return ApiResponse.success(data=result)


@router.post("/sync-async")
@handle_api_errors
async def sync_async(
    exchange: Optional[str] = Query(None, description="交易所代码（可选，默认同步 SSE 和 SZSE）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步交易日历数据（通过 Celery）

    该接口立即返回 Celery 任务 ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。
    """
    from app.tasks.trade_cal_tasks import sync_trade_cal_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    start_date_fmt = start_date.replace('-', '') if start_date else None
    end_date_fmt = end_date.replace('-', '') if end_date else None

    # 提交 Celery 任务
    celery_task = sync_trade_cal_task.apply_async(
        kwargs={
            'exchange': exchange,
            'start_date': start_date_fmt,
            'end_date': end_date_fmt
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_trade_cal',
        display_name='交易日历',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'exchange': exchange,
            'start_date': start_date_fmt,
            'end_date': end_date_fmt
        },
        source='trade_cal_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="交易日历同步任务已提交"
    )
