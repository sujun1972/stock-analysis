"""
涨跌停列表 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date

from app.services.limit_list_service import LimitListService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_limit_list(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数限制")
):
    """
    查询涨跌停列表数据

    Args:
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 股票代码
        limit_type: 涨跌停类型（U涨停D跌停Z炸板）
        limit: 返回记录数限制

    Returns:
        涨跌停列表数据
    """
    service = LimitListService()

    # 日期格式转换（date -> YYYYMMDD）
    start_date_str = start_date.strftime('%Y%m%d') if start_date else None
    end_date_str = end_date.strftime('%Y%m%d') if end_date else None

    result = await service.get_limit_list_data(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=ts_code,
        limit_type=limit_type,
        limit=limit
    )

    return ApiResponse.success(data=result)


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）")
):
    """
    获取涨跌停列表统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期
        limit_type: 涨跌停类型

    Returns:
        统计信息
    """
    service = LimitListService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y%m%d') if start_date else None
    end_date_str = end_date.strftime('%Y%m%d') if end_date else None

    result = await service.get_limit_list_data(
        start_date=start_date_str,
        end_date=end_date_str,
        limit_type=limit_type,
        limit=0  # 只获取统计信息
    )

    return ApiResponse.success(data={'statistics': result.get('statistics', {})})


@router.get("/latest")
async def get_latest(
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）")
):
    """
    获取最新交易日的涨跌停列表数据

    Args:
        limit_type: 涨跌停类型

    Returns:
        最新涨跌停列表数据
    """
    service = LimitListService()
    result = await service.get_latest_data(limit_type=limit_type)

    return ApiResponse.success(data=result)


@router.get("/top-limit-up")
async def get_top_limit_up(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为最新日期）"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数限制")
):
    """
    获取涨停股票排行榜（按连板数和涨幅排序）

    Args:
        trade_date: 交易日期（可选）
        limit: 返回记录数限制

    Returns:
        涨停股票排行榜
    """
    service = LimitListService()

    # 日期格式转换
    trade_date_str = trade_date.strftime('%Y%m%d') if trade_date else None

    result = await service.get_top_limit_up_stocks(
        trade_date=trade_date_str,
        limit=limit
    )

    return ApiResponse.success(data={'items': result, 'total': len(result)})


@router.post("/sync-async")
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选）"),
    start_date: Optional[date] = Query(None, description="开始日期（可选）"),
    end_date: Optional[date] = Query(None, description="结束日期（可选）"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit_type: Optional[str] = Query(None, description="涨跌停类型（U涨停D跌停Z炸板）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步涨跌停列表数据（使用 Celery）

    Args:
        trade_date: 交易日期（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        ts_code: 股票代码（可选）
        limit_type: 涨跌停类型（可选）
        current_user: 当前用户（需要管理员权限）

    Returns:
        任务提交结果
    """
    from app.tasks.limit_list_tasks import sync_limit_list_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    trade_date_formatted = trade_date.strftime('%Y%m%d') if trade_date else None
    start_date_formatted = start_date.strftime('%Y%m%d') if start_date else None
    end_date_formatted = end_date.strftime('%Y%m%d') if end_date else None

    # 提交 Celery 任务
    celery_task = sync_limit_list_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'ts_code': ts_code,
            'limit_type': limit_type
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
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

    # 构造提示消息
    if trade_date:
        date_msg = f"涨跌停列表同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    elif start_date and end_date:
        date_msg = f"涨跌停列表同步任务已提交（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "涨跌停列表同步任务已提交"

    return ApiResponse.success(
        data=task_data,
        message=date_msg
    )
