"""
龙虎榜每日明细 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date

from app.services.top_list_service import TopListService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_top_list(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制")
):
    """
    查询龙虎榜数据

    Args:
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 股票代码
        limit: 返回记录数限制

    Returns:
        龙虎榜数据列表
    """
    service = TopListService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    result = await service.get_top_list_data(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=ts_code,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期")
):
    """
    获取龙虎榜统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计信息
    """
    service = TopListService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    result = await service.get_statistics(
        start_date=start_date_str,
        end_date=end_date_str
    )

    return ApiResponse.success(data=result)


@router.get("/latest")
async def get_latest():
    """
    获取最新交易日的龙虎榜数据

    Returns:
        最新龙虎榜数据
    """
    service = TopListService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)


@router.get("/top-rank")
async def get_top_rank(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数")
):
    """
    获取净买入额排名TOP数据

    Args:
        trade_date: 交易日期
        limit: 返回记录数

    Returns:
        排名TOP数据列表
    """
    service = TopListService()

    # 日期格式转换
    trade_date_str = trade_date.strftime('%Y-%m-%d') if trade_date else None

    result = await service.get_top_by_net_amount(
        trade_date=trade_date_str,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.post("/sync-async")
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为今天）"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步龙虎榜数据（使用 Celery）

    Args:
        trade_date: 交易日期（可选，默认为今天）
        ts_code: 股票代码（可选）
        current_user: 当前用户（需要管理员权限）

    Returns:
        任务提交结果
    """
    from app.tasks.top_list_tasks import sync_top_list_task
    from datetime import datetime

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    # 如果未提供日期，使用今天
    if trade_date:
        trade_date_formatted = trade_date.strftime('%Y%m%d')
    else:
        trade_date_formatted = None  # Service 层会使用今天

    # 提交 Celery 任务
    celery_task = sync_top_list_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_top_list',
        display_name='龙虎榜每日明细',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code
        },
        source='top_list_page'
    )

    # 构造提示消息
    if trade_date:
        date_msg = f"龙虎榜数据同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "龙虎榜数据同步任务已提交"

    return ApiResponse.success(
        data=task_data,
        message=date_msg
    )
