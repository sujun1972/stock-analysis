"""
龙虎榜机构明细 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date

from app.services.top_inst_service import TopInstService
from app.services import TaskHistoryHelper
from app.services.stock_quote_cache import stock_quote_cache
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_top_inst(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    side: Optional[str] = Query(None, description="买卖类型（0：买入，1：卖出）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=200, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc/desc")
):
    """查询龙虎榜机构明细数据（支持分页和排序）"""
    service = TopInstService()

    if trade_date:
        start_date_str = trade_date.strftime('%Y-%m-%d')
        end_date_str = trade_date.strftime('%Y-%m-%d')
    elif start_date or end_date:
        start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    else:
        # 未传日期：先查今天，无数据则回退到最近有数据的交易日
        resolved = await service.resolve_default_trade_date()
        start_date_str = resolved
        end_date_str = resolved

    # 自动补全股票代码后缀（用户输入 '000001' → '000001.SZ'）
    resolved_ts_code = await stock_quote_cache.resolve_ts_code(ts_code) if ts_code else None

    result = await service.get_top_inst_data(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=resolved_ts_code,
        side=side,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )
    result['trade_date'] = start_date_str

    return ApiResponse.success(data=result)


@router.get("/statistics")
async def get_statistics(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """获取龙虎榜机构明细统计信息"""
    service = TopInstService()

    if trade_date:
        start_date_str = trade_date.strftime('%Y-%m-%d')
        end_date_str = trade_date.strftime('%Y-%m-%d')
    elif start_date or end_date:
        start_date_str = start_date.strftime('%Y-%m-%d') if start_date else None
        end_date_str = end_date.strftime('%Y-%m-%d') if end_date else None
    else:
        resolved = await service.resolve_default_trade_date()
        start_date_str = resolved
        end_date_str = resolved

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
