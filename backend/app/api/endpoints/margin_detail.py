"""
融资融券交易明细API端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from loguru import logger

from app.core.dependencies import require_admin
from app.models.user import User
from app.services.margin_detail_service import MarginDetailService
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_margin_detail(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券交易明细数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        page: 页码
        page_size: 每页数量
        current_user: 当前登录用户（管理员）

    Returns:
        融资融券交易明细数据列表
    """
    try:
        service = MarginDetailService()
        result = await service.get_margin_detail_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            page=page,
            page_size=page_size
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取融资融券交易明细失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_margin_detail_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券交易明细统计数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        统计数据
    """
    try:
        service = MarginDetailService()
        statistics = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取融资融券交易明细统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-stocks")
async def get_top_stocks(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user: User = Depends(require_admin)
):
    """
    获取融资融券余额TOP股票

    Args:
        trade_date: 交易日期，格式：YYYY-MM-DD
        limit: 返回数量
        current_user: 当前登录用户（管理员）

    Returns:
        TOP股票列表
    """
    try:
        service = MarginDetailService()
        top_stocks = await service.get_top_stocks(
            trade_date=trade_date,
            limit=limit
        )
        return ApiResponse.success(data=top_stocks)

    except Exception as e:
        logger.error(f"获取TOP股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_margin_detail_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步融资融券交易明细数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.margin_detail_tasks import sync_margin_detail_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_margin_detail_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'ts_code': ts_code,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 记录任务到celery_task_history表，用于任务面板显示
        db_manager = DatabaseManager()
        history_query = """
            INSERT INTO celery_task_history
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        task_params = {
            'trade_date': trade_date_formatted,
            'ts_code': ts_code,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }

        task_metadata = {
            "trigger": "manual",
            "source": "margin_detail_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_margin_detail',
                '融资融券交易明细',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"融资融券交易明细同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_margin_detail",
                "display_name": "融资融券交易明细",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交融资融券交易明细同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
