"""
股票日线数据 API

提供日线数据查询和同步功能
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin, get_current_user
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stock_daily_service import StockDailyService
from app.services import TaskHistoryHelper

router = APIRouter()


# ==================== Request Models ====================


class SyncDailyRequest(BaseModel):
    """同步日线数据请求"""
    code: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    years: int = 5


# ==================== Query Endpoints ====================


@router.get("")
@handle_api_errors
async def get_daily_data(
    code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user)
):
    """
    查询日线数据

    - 如果指定 code，返回该股票的历史数据
    - 如果不指定 code，返回所有股票的最新数据（分页）
    """
    service = StockDailyService()
    result = await service.get_daily_data(
        code=code,
        start_date=start_date,
        end_date=end_date,
        limit=page_size,
        page=page
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
@handle_api_errors
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_user)
):
    """
    获取日线数据统计信息

    返回数据覆盖范围、股票数量、记录数量等统计
    """
    service = StockDailyService()
    result = await service.get_statistics(
        start_date=start_date,
        end_date=end_date
    )

    return ApiResponse.success(data=result)


# ==================== Sync Endpoints ====================


@router.post("/sync")
@handle_api_errors
async def sync_single_stock(
    request: SyncDailyRequest,
    current_user: User = Depends(require_admin)
):
    """
    同步单只股票日线数据（同步执行）

    适用于单只股票的即时同步
    """
    if not request.code:
        return ApiResponse.error(message="请指定股票代码", code=400)

    service = StockDailyService()
    result = await service.sync_single_stock(
        code=request.code,
        start_date=request.start_date,
        end_date=request.end_date,
        years=request.years
    )

    if result['status'] == 'success':
        return ApiResponse.success(data=result, message="同步完成")
    else:
        return ApiResponse.error(message=result.get('error', '同步失败'), code=500)


@router.post("/sync-async")
@handle_api_errors
async def sync_async(
    request: SyncDailyRequest,
    current_user: User = Depends(require_admin)
):
    """
    异步同步日线数据（使用 Celery）

    支持：
    - 单只股票同步：指定 code 参数
    - 全市场同步：不指定 code，使用最近交易日
    """
    from app.tasks.sync_tasks import sync_daily_single_task

    # 日期格式转换 (YYYY-MM-DD -> YYYYMMDD)
    start_date_fmt = request.start_date.replace('-', '') if request.start_date else None
    end_date_fmt = request.end_date.replace('-', '') if request.end_date else None

    # 提交 Celery 任务
    celery_task = sync_daily_single_task.apply_async(
        kwargs={
            'code': request.code,  # 可以为 None，将在任务中处理
            'start_date': start_date_fmt,
            'end_date': end_date_fmt,
            'years': request.years
        }
    )

    # 任务显示名称
    if request.code:
        display_name = f'日线数据同步({request.code})'
    else:
        display_name = '日线数据同步(全市场)'

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_daily_single',
        display_name=display_name,
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'code': request.code,
            'start_date': start_date_fmt,
            'end_date': end_date_fmt,
            'years': request.years
        },
        source='stock_daily_page'
    )

    return ApiResponse.success(
        data=task_data,
        message="同步任务已提交"
    )
