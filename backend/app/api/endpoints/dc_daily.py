"""
东方财富概念板块行情 API 端点
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.dc_daily_service import DcDailyService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_dc_daily(
    ts_code: Optional[str] = Query(None, description="板块代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD，不传则自动使用最近有数据的交易日"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD（与trade_date二选一）"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=2000),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc/desc")
):
    """
    查询东方财富概念板块行情数据

    Args:
        ts_code: 板块代码
        trade_date: 单日交易日期（YYYY-MM-DD），优先于 start_date/end_date
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        page: 页码
        page_size: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        东方财富概念板块行情数据列表，含 trade_date 字段用于前端回填日期选择器
    """
    try:
        service = DcDailyService()

        if trade_date:
            start_date_str = trade_date
            end_date_str = trade_date
        elif start_date or end_date:
            start_date_str = start_date
            end_date_str = end_date
        else:
            # 未传日期：自动解析最近有数据的交易日
            resolved = await service.resolve_default_trade_date()
            start_date_str = resolved
            end_date_str = resolved

        result = await service.get_dc_daily_data(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        result['trade_date'] = start_date_str

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询东方财富概念板块行情数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="板块代码")
):
    """
    获取东方财富概念板块行情统计信息

    Returns:
        统计信息
    """
    try:
        service = DcDailyService()
        if trade_date:
            start_date_str = trade_date
            end_date_str = trade_date
        else:
            start_date_str = start_date
            end_date_str = end_date

        stats = await service.get_statistics(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新的东方财富概念板块行情数据

    Returns:
        最新数据
    """
    try:
        service = DcDailyService()
        result = await service.get_latest_data()

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_dc_daily_async(
    ts_code: Optional[str] = Query(None, description="板块代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    idx_type: Optional[str] = Query(None, description="板块类型（概念板块/行业板块/地域板块）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步东方财富概念板块行情数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 板块代码
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        idx_type: 板块类型（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.dc_daily_tasks import sync_dc_daily_task

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        celery_task = sync_dc_daily_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'idx_type': idx_type
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_dc_daily',
            display_name='东方财富概念板块行情',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'idx_type': idx_type
            },
            source='dc_daily_page'
        )

        logger.info(f"东方财富概念板块行情同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交东方财富概念板块行情同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
