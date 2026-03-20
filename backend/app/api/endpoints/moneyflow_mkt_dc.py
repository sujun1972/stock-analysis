"""
大盘资金流向API（东方财富DC）

提供大盘主力资金流向数据接口，包含超大单、大单、中单、小单的流入流出情况，
支持查询历史数据、同步最新数据、获取最新资金流向等功能。
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.moneyflow_mkt_dc_service import MoneyflowMktDcService

router = APIRouter()


@router.get("")
async def get_moneyflow_mkt_dc(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=365, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """获取大盘资金流向数据"""
    try:
        service = MoneyflowMktDcService()
        result = await asyncio.to_thread(
            service.get_moneyflow_data,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result, message="获取大盘资金流向成功")
    except Exception as e:
        logger.error(f"获取大盘资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow_mkt_dc(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """同步大盘资金流向数据（管理员功能）"""
    try:
        from app.services.extended_sync_service import ExtendedDataSyncService
        service = ExtendedDataSyncService()
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        result = await service.sync_moneyflow_mkt_dc(
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        if result["status"] == "success":
            return ApiResponse.success(data=result, message=f"成功同步 {result['records']} 条大盘资金流向数据")
        else:
            return ApiResponse.error(message=result.get("error", "同步失败"))
    except Exception as e:
        logger.error(f"同步大盘资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_mkt_dc_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """异步同步大盘资金流向数据（通过Celery任务）"""
    try:
        from app.tasks.moneyflow_mkt_dc_tasks import sync_moneyflow_mkt_dc_task
        from app.services import TaskHistoryHelper

        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        celery_task = sync_moneyflow_mkt_dc_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_moneyflow_mkt_dc',
            display_name='大盘资金流向',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='moneyflow_mkt_dc_page'
        )

        logger.info(f"大盘资金流向同步任务已提交: {celery_task.id}")
        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )
    except Exception as e:
        logger.error(f"提交大盘资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_moneyflow_mkt_dc(current_user: User = Depends(get_current_user)):
    """获取最新的大盘资金流向数据"""
    try:
        service = MoneyflowMktDcService()
        data = await asyncio.to_thread(service.get_latest_moneyflow)
        if not data:
            return ApiResponse.success(data=None, message="暂无大盘资金流向数据")
        return ApiResponse.success(data=data, message="获取最新大盘资金流向成功")
    except Exception as e:
        logger.error(f"获取最新大盘资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
