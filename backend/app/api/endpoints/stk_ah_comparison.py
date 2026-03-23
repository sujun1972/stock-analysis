"""
AH股比价数据 API端点
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.user import User
from app.services.stk_ah_comparison_service import StkAhComparisonService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_stk_ah_comparison(
    hk_code: Optional[str] = Query(None, description="港股代码，如：02068.HK"),
    ts_code: Optional[str] = Query(None, description="A股代码，如：601068.SH"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="返回记录数", ge=1, le=1000)
):
    """
    查询AH股比价数据

    Args:
        hk_code: 港股代码（可选）
        ts_code: A股代码（可选）
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        limit: 返回记录数

    Returns:
        AH股比价数据列表和统计信息
    """
    try:
        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        service = StkAhComparisonService()
        result = await service.get_stk_ah_comparison_data(
            hk_code=hk_code,
            ts_code=ts_code,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询AH股比价数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取AH股比价统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计信息
    """
    try:
        # 转换日期格式
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        service = StkAhComparisonService()
        result = await service.get_stk_ah_comparison_data(
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            limit=1
        )

        return ApiResponse.success(data=result["statistics"])

    except Exception as e:
        logger.error(f"获取AH股比价统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新交易日期

    Returns:
        最新交易日期
    """
    try:
        service = StkAhComparisonService()
        latest_date = await service.get_latest_trade_date()

        return ApiResponse.success(data={"latest_trade_date": latest_date})

    except Exception as e:
        logger.error(f"获取最新交易日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-premium")
async def get_top_premium(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD，默认最新交易日"),
    limit: int = Query(20, description="返回记录数", ge=1, le=100)
):
    """
    获取溢价率最高的股票

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD，默认最新交易日
        limit: 返回记录数

    Returns:
        溢价率最高的股票列表
    """
    try:
        # 转换日期格式
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None

        service = StkAhComparisonService()
        result = await service.get_top_premium(
            trade_date=trade_date_formatted,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取溢价率最高股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_ah_comparison_async(
    hk_code: Optional[str] = Query(None, description="港股代码，格式：xxxxx.HK"),
    ts_code: Optional[str] = Query(None, description="A股代码，格式：xxxxxx.SH/SZ/BJ"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步AH股比价数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    注意：所有参数均为可选，不传参数时将同步最近30天数据

    Args:
        hk_code: 港股代码（可选）
        ts_code: A股代码（可选）
        trade_date: 单个交易日期（可选），格式：YYYY-MM-DD
        start_date: 开始日期（可选），格式：YYYY-MM-DD
        end_date: 结束日期（可选），格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_ah_comparison_tasks import sync_stk_ah_comparison_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        hk_code_formatted = hk_code.strip() if hk_code else None
        ts_code_formatted = ts_code.strip() if ts_code else None
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_stk_ah_comparison_task.apply_async(
            kwargs={
                'hk_code': hk_code_formatted,
                'ts_code': ts_code_formatted,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_ah_comparison',
            display_name='AH股比价数据',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'hk_code': hk_code_formatted,
                'ts_code': ts_code_formatted,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='stk_ah_comparison_page'
        )

        logger.info(f"AH股比价同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交AH股比价同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
