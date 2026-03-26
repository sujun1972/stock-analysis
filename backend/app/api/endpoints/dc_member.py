"""
东方财富板块成分数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.dc_member_service import DcMemberService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_dc_member(
    ts_code: Optional[str] = Query(None, description="板块指数代码（如 BK1184.DC）"),
    con_code: Optional[str] = Query(None, description="成分股票代码（如 002117.SZ）"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD（优先于 start/end）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, description="页码，从 1 开始", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=1000),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: str = Query('desc', description="排序方向：asc 或 desc")
):
    """
    查询东方财富板块成分数据（支持分页和后端排序）

    Args:
        ts_code: 板块指数代码（如 BK1184.DC）
        con_code: 成分股票代码（如 002117.SZ）
        trade_date: 单日交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        page: 页码
        page_size: 每页记录数
        sort_by: 排序字段
        sort_order: 排序方向

    Returns:
        东方财富板块成分数据列表
    """
    try:
        service = DcMemberService()
        result = await service.get_dc_member_data(
            ts_code=ts_code,
            con_code=con_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询东方财富板块成分数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="板块代码")
):
    """
    获取东方财富板块成分数据统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        trade_date: 单日交易日期，格式：YYYY-MM-DD
        ts_code: 板块代码

    Returns:
        统计信息
    """
    try:
        service = DcMemberService()
        stats = await service.get_statistics(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            trade_date=trade_date
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新的东方财富板块成分数据

    Returns:
        最新数据
    """
    try:
        service = DcMemberService()
        result = await service.get_latest_data()

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_dc_member_async(
    ts_code: Optional[str] = Query(None, description="板块指数代码（如 BK1184.DC）"),
    con_code: Optional[str] = Query(None, description="成分股票代码（如 002117.SZ）"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步东方财富板块成分数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 板块指数代码（如 BK1184.DC）
        con_code: 成分股票代码（如 002117.SZ）
        trade_date: 交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.dc_member_tasks import sync_dc_member_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_dc_member_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'con_code': con_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_dc_member',
            display_name='东方财富板块成分',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'con_code': con_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='dc_member_page'
        )

        logger.info(f"东方财富板块成分同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交东方财富板块成分同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
