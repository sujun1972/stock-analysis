"""
连板天梯 API 端点
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional
from datetime import date

from app.services.limit_step_service import LimitStepService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_limit_step(
    trade_date: Optional[date] = Query(None, description="交易日期（单日查询）"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    nums: Optional[str] = Query(None, description="连板次数（支持多个，如 2,3）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc/desc")
):
    """
    查询连板天梯数据（支持分页）

    Args:
        trade_date: 单日交易日期
        start_date: 开始日期
        end_date: 结束日期
        ts_code: 股票代码
        nums: 连板次数（支持多个，如 "2,3"）
        page: 页码
        page_size: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        连板天梯数据
    """
    service = LimitStepService()

    if trade_date:
        start_date_str = end_date_str = trade_date.strftime('%Y%m%d')
        resolved_date = trade_date.strftime('%Y-%m-%d')
    elif start_date or end_date:
        start_date_str = start_date.strftime('%Y%m%d') if start_date else None
        end_date_str = end_date.strftime('%Y%m%d') if end_date else None
        # 回传给前端的展示日期，取区间起点（YYYY-MM-DD）
        resolved_date = start_date.strftime('%Y-%m-%d') if start_date else None
    else:
        # 未传日期：自动解析最近有数据的交易日（YYYY-MM-DD格式）
        resolved_date = await service.resolve_default_trade_date()
        if resolved_date:
            d = resolved_date.replace('-', '')
            start_date_str = end_date_str = d
        else:
            start_date_str = end_date_str = None

    offset = (page - 1) * page_size

    result = await service.get_limit_step_data(
        start_date=start_date_str,
        end_date=end_date_str,
        ts_code=ts_code,
        nums=nums,
        limit=page_size,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )
    result['trade_date'] = resolved_date

    return ApiResponse.success(data=result)


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    nums: Optional[str] = Query(None, description="连板次数（支持多个，如 2,3）")
):
    """
    获取连板天梯统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期
        nums: 连板次数

    Returns:
        统计信息
    """
    service = LimitStepService()

    # 日期格式转换
    start_date_str = start_date.strftime('%Y%m%d') if start_date else None
    end_date_str = end_date.strftime('%Y%m%d') if end_date else None

    result = await service.get_limit_step_data(
        start_date=start_date_str,
        end_date=end_date_str,
        nums=nums,
        limit=0  # 只获取统计信息
    )

    return ApiResponse.success(data={'statistics': result.get('statistics', {})})


@router.get("/latest")
async def get_latest(
    nums: Optional[str] = Query(None, description="连板次数（支持多个，如 2,3）"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数限制")
):
    """
    获取最新交易日的连板天梯数据

    Args:
        nums: 连板次数
        limit: 返回记录数限制

    Returns:
        最新连板天梯数据
    """
    service = LimitStepService()
    result = await service.get_latest_data(limit=limit)

    # 如果指定了连板次数，筛选数据
    if nums and result.get('items'):
        nums_list = [n.strip() for n in nums.split(',')]
        result['items'] = [
            item for item in result['items']
            if item.get('nums') in nums_list
        ]
        result['total'] = len(result['items'])

    return ApiResponse.success(data=result)


@router.get("/top")
async def get_top(
    trade_date: Optional[date] = Query(None, description="交易日期（可选，默认为最新日期）"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数限制"),
    ascending: bool = Query(False, description="是否升序排列")
):
    """
    获取连板次数排行榜

    Args:
        trade_date: 交易日期（可选）
        limit: 返回记录数限制
        ascending: 是否升序排列（False=降序，True=升序）

    Returns:
        连板次数排行榜
    """
    service = LimitStepService()

    # 日期格式转换
    trade_date_str = trade_date.strftime('%Y%m%d') if trade_date else None

    result = await service.get_top_by_nums(
        trade_date=trade_date_str,
        limit=limit,
        ascending=ascending
    )

    return ApiResponse.success(data={'items': result, 'total': len(result)})


@router.post("/sync-async")
async def sync_async(
    trade_date: Optional[date] = Query(None, description="交易日期（可选）"),
    start_date: Optional[date] = Query(None, description="开始日期（可选）"),
    end_date: Optional[date] = Query(None, description="结束日期（可选）"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    nums: Optional[str] = Query(None, description="连板次数（支持多个，如 2,3）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步连板天梯数据（使用 Celery）

    Args:
        trade_date: 交易日期（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        ts_code: 股票代码（可选）
        nums: 连板次数（可选）
        current_user: 当前用户（需要管理员权限）

    Returns:
        任务提交结果
    """
    from app.tasks.limit_step_tasks import sync_limit_step_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    trade_date_formatted = trade_date.strftime('%Y%m%d') if trade_date else None
    start_date_formatted = start_date.strftime('%Y%m%d') if start_date else None
    end_date_formatted = end_date.strftime('%Y%m%d') if end_date else None

    # 提交 Celery 任务
    celery_task = sync_limit_step_task.apply_async(
        kwargs={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'ts_code': ts_code,
            'nums': nums
        }
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_limit_step',
        display_name='连板天梯',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'ts_code': ts_code,
            'nums': nums
        },
        source='limit_step_page'
    )

    # 构造提示消息
    if trade_date:
        date_msg = f"连板天梯同步任务已提交（{trade_date.strftime('%Y-%m-%d')}）"
    elif start_date and end_date:
        date_msg = f"连板天梯同步任务已提交（{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}）"
    else:
        date_msg = "连板天梯同步任务已提交"

    return ApiResponse.success(
        data=task_data,
        message=date_msg
    )
