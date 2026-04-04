"""
每日指标数据API端点

提供每日指标数据（换手率、市盈率、市净率等）的查询和同步功能
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.daily_basic_service import DailyBasicService
from app.services import TaskHistoryHelper

router = APIRouter(tags=["daily_basic"])


@router.get("")
async def get_daily_basic_list(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量")
):
    """
    查询每日指标数据

    Args:
        trade_date: 交易日期（单日查询）
        ts_code: 股票代码（可选）
        start_date: 开始日期
        end_date: 结束日期
        page: 页码
        page_size: 每页数量

    Returns:
        每日指标数据列表
    """
    try:
        service = DailyBasicService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 查询数据
        result = await service.get_daily_basic_list(
            trade_date=trade_date_formatted,
            ts_code=ts_code,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            page=page,
            page_size=page_size
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询每日指标数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_daily_basic_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取每日指标统计信息

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计信息
    """
    try:
        service = DailyBasicService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 查询统计信息
        stats = await service.get_statistics(
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取每日指标统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_daily_basic():
    """
    获取最新交易日的每日指标数据

    Returns:
        最新交易日的数据
    """
    try:
        service = DailyBasicService()
        result = await service.get_latest_data()
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新每日指标数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_daily_basic_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步每日指标数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.daily_basic_tasks import sync_daily_basic_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_daily_basic_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'ts_code': ts_code,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_daily_basic',
            display_name='每日指标',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'ts_code': ts_code,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='daily_basic_page'
        )

        logger.info(f"每日指标同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交每日指标同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_daily_basic_full_history(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYYMMDD，默认 20210101"),
    current_user: User = Depends(require_admin)
):
    """
    全量历史同步：逐只股票同步每日指标，8 并发，支持中断续继

    每只股票单独请求 Tushare，避免单次返回上限 6000 条的问题。
    支持 Redis 进度续继，任务中断后重新触发会自动跳过已完成股票。
    """
    try:
        from app.tasks.daily_basic_tasks import sync_daily_basic_full_history_task

        celery_task = sync_daily_basic_full_history_task.apply_async(
            kwargs={'start_date': start_date}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_daily_basic_full_history',
            display_name='每日指标（全量）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date},
            source='daily_basic_page'
        )

        logger.info(f"每日指标全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交每日指标全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
