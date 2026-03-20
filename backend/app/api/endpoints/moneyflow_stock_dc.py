"""个股资金流向API（东方财富DC）"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.moneyflow_stock_dc_service import MoneyflowStockDcService

router = APIRouter()


@router.get("")
async def get_moneyflow_stock_dc(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取个股资金流向数据"""
    try:
        service = MoneyflowStockDcService()
        result = await asyncio.to_thread(
            service.get_moneyflow_data,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result, message="获取个股资金流向成功")
    except Exception as e:
        logger.error(f"获取个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow_stock_dc(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """同步个股资金流向数据（管理员功能）"""
    try:
        from app.services.extended_sync_service import ExtendedDataSyncService
        service = ExtendedDataSyncService()
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        result = await service.sync_moneyflow_stock_dc(
            ts_code=ts_code,
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        if result["status"] == "success":
            return ApiResponse.success(data=result, message=f"成功同步 {result['records']} 条个股资金流向数据")
        else:
            return ApiResponse.error(message=result.get("error", "同步失败"))
    except Exception as e:
        logger.error(f"同步个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_stock_dc_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步个股资金流向数据"""
    try:
        from app.tasks.moneyflow_stock_dc_tasks import sync_moneyflow_stock_dc_task
        from src.database.db_manager import DatabaseManager

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        celery_task = sync_moneyflow_stock_dc_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        db_manager = DatabaseManager()
        await asyncio.to_thread(
            db_manager._execute_update,
            """INSERT INTO celery_task_history
               (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
            (
                celery_task.id, 'tasks.sync_moneyflow_stock_dc', '个股资金流向', 'data_sync',
                current_user.id, 'pending',
                json.dumps({'ts_code': ts_code, 'trade_date': trade_date_formatted,
                            'start_date': start_date_formatted, 'end_date': end_date_formatted}),
                json.dumps({"trigger": "manual", "source": "moneyflow_stock_dc_page"})
            )
        )

        logger.info(f"个股资金流向同步任务已提交: {celery_task.id}")
        return ApiResponse.success(
            data={"celery_task_id": celery_task.id, "task_name": "tasks.sync_moneyflow_stock_dc",
                  "display_name": "个股资金流向", "status": "pending"},
            message="任务已提交，正在后台执行"
        )
    except Exception as e:
        logger.error(f"提交个股资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_moneyflow_stocks(
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(get_current_user)
):
    """获取主力资金流入排名前N的股票"""
    try:
        service = MoneyflowStockDcService()
        result = await asyncio.to_thread(service.get_top_stocks, trade_date=trade_date, limit=limit)
        return ApiResponse.success(data=result, message="获取资金流入排名成功")
    except Exception as e:
        logger.error(f"获取资金流入排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
