"""
利润表数据API端点
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.income_service import IncomeService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_income_data(
    start_date: Optional[str] = Query(None, description="开始日期（报告期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（报告期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_type: Optional[str] = Query(None, description="报告类型（1-12）"),
    comp_type: Optional[str] = Query(None, description="公司类型（1-4）"),
    limit: int = Query(30, ge=1, le=1000, description="限制返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量（分页）")
):
    """
    查询利润表数据

    Args:
        start_date: 开始日期（报告期）
        end_date: 结束日期（报告期）
        ts_code: 股票代码
        report_type: 报告类型
        comp_type: 公司类型
        limit: 限制返回记录数

    Returns:
        利润表数据列表
    """
    try:
        service = IncomeService()
        result = await service.get_income_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            report_type=report_type,
            comp_type=comp_type,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询利润表数据失败: {e}")
        return ApiResponse.error(message=f"查询失败: {str(e)}")


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（报告期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（报告期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    report_type: Optional[str] = Query(None, description="报告类型")
):
    """
    获取利润表统计信息

    Args:
        start_date: 开始日期（报告期）
        end_date: 结束日期（报告期）
        ts_code: 股票代码
        report_type: 报告类型

    Returns:
        统计信息
    """
    try:
        service = IncomeService()
        result = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            report_type=report_type
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取利润表统计信息失败: {e}")
        return ApiResponse.error(message=f"获取统计信息失败: {str(e)}")


@router.get("/latest")
async def get_latest_income(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新利润表数据

    Args:
        ts_code: 股票代码

    Returns:
        最新利润表记录
    """
    try:
        service = IncomeService()
        result = await service.get_latest_data(ts_code=ts_code)

        if result:
            return ApiResponse.success(data=result)
        else:
            return ApiResponse.success(data=None, message="暂无数据")

    except Exception as e:
        logger.error(f"获取最新利润表数据失败: {e}")
        return ApiResponse.error(message=f"获取最新数据失败: {str(e)}")


@router.post("/sync-async")
async def sync_income_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    period: Optional[str] = Query(None, description="报告期（YYYYMMDD或YYYYQQ格式）"),
    start_date: Optional[str] = Query(None, description="开始日期（YYYYMMDD）"),
    end_date: Optional[str] = Query(None, description="结束日期（YYYYMMDD）"),
    report_type: Optional[str] = Query(None, description="报告类型（1-12）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步利润表数据（使用 Celery）

    Args:
        ts_code: 股票代码
        period: 报告期
        start_date: 开始日期
        end_date: 结束日期
        report_type: 报告类型
        current_user: 当前用户

    Returns:
        任务信息
    """
    try:
        from app.tasks.income_tasks import sync_income_task

        # 提交 Celery 任务
        celery_task = sync_income_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'report_type': report_type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_income',
            display_name='利润表数据同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'report_type': report_type
            },
            source='income_page'
        )

        return ApiResponse.success(
            data=task_data,
            message="利润表同步任务已提交，请在任务面板查看进度"
        )

    except Exception as e:
        logger.error(f"提交利润表同步任务失败: {e}")
        return ApiResponse.error(message=f"任务提交失败: {str(e)}")
