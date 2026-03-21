"""
龙虎榜机构明细 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date

from app.services.top_inst_service import TopInstService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_top_inst(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    side: Optional[str] = Query(None, description="买卖类型（0：买入，1：卖出）"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数限制")
):
    """
    查询龙虎榜机构明细数据

    Args:
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 股票代码
        side: 买卖类型（0：买入，1：卖出）
        limit: 返回记录数限制

    Returns:
        龙虎榜机构明细数据列表
    """
    service = TopInstService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    result = await service.get_top_inst_data(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=ts_code,
        side=side,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取龙虎榜机构明细统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 股票代码

    Returns:
        统计信息
    """
    service = TopInstService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None

    result = await service.get_statistics(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=ts_code
    )

    return ApiResponse.success(data=result)


@router.get("/latest")
async def get_latest():
    """
    获取最新交易日的龙虎榜机构明细数据

    Returns:
        最新龙虎榜机构明细数据
    """
    service = TopInstService()
    result = await service.get_latest_data()

    return ApiResponse.success(data=result)


@router.post("/sync-async")
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为前一个交易日）"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步龙虎榜机构明细数据（使用 Celery）

    Args:
        trade_date: 交易日期（可选，默认为前一个交易日）
        ts_code: 股票代码（可选）
        current_user: 当前用户（需要管理员权限）

    Returns:
        任务提交结果
    """
    from app.tasks.top_inst_tasks import sync_top_inst_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    if trade_date:
        trade_date_formatted = trade_date.strftime('%Y%m%d')
    else:
        trade_date_formatted = None  # Service 层会使用前一个交易日

    # 提交 Celery 任务
    celery_task = sync_top_inst_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_top_inst',
        display_name='龙虎榜机构明细',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'ts_code': ts_code
        },
        source='top_inst_page'
    )

    # 构造提示消息
    if trade_date:
        date_msg = f"龙虎榜机构明细同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "龙虎榜机构明细同步任务已提交"

    return ApiResponse.success(
        data=task_data,
        message=date_msg
    )
