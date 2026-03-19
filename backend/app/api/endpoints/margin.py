"""
融资融券交易汇总 API
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User
from app.services.margin_service import MarginService

router = APIRouter()


@router.get("")
async def get_margin_data(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    exchange_id: Optional[str] = Query(None, description="交易所代码（SSE/SZSE/BSE）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量")
):
    """
    获取融资融券交易汇总数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）
        page: 页码（默认1）
        page_size: 每页数量（默认30，最大100）

    Returns:
        融资融券交易汇总数据列表
    """
    try:
        margin_service = MarginService()
        result = await margin_service.get_margin_data(
            start_date=start_date,
            end_date=end_date,
            exchange_id=exchange_id,
            page=page,
            page_size=page_size
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取融资融券交易汇总数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_margin_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取融资融券交易汇总统计数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD

    Returns:
        统计数据（平均融资融券余额、总余额、最大融资余额、最大融券余额）
    """
    try:
        margin_service = MarginService()
        result = await margin_service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取融资融券统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_margin_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    exchange_id: Optional[str] = Query(None, description="交易所代码（SSE/SZSE/BSE）"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步融资融券交易汇总数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.margin_tasks import sync_margin_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_margin_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'exchange_id': exchange_id
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
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'exchange_id': exchange_id
        }

        task_metadata = {
            "trigger": "manual",
            "source": "margin_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_margin',
                '融资融券交易汇总',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"融资融券交易汇总同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_margin",
                "display_name": "融资融券交易汇总",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交融资融券交易汇总同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
