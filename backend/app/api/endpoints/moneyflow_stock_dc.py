"""个股资金流向API（东方财富DC）"""

import asyncio
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
    ts_code: Optional[str] = Query(None, description="股票代码，如 000001.SZ"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD（优先于 start/end_date）"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页记录数"),
    sort_by: Optional[str] = Query(None, description="排序字段"),
    sort_order: Optional[str] = Query(None, description="排序方向：asc/desc"),
    current_user: User = Depends(get_current_user)
):
    """获取个股资金流向数据（支持单日查询、分页、排序）"""
    try:
        service = MoneyflowStockDcService()
        result = await asyncio.to_thread(
            service.get_moneyflow_data,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            page=page,
            sort_by=sort_by,
            sort_order=sort_order,
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
        from app.services import TaskHistoryHelper

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

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_moneyflow_stock_dc',
            display_name='个股资金流向',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='moneyflow_stock_dc_page'
        )

        logger.info(f"个股资金流向同步任务已提交: {celery_task.id}")
        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )
    except Exception as e:
        logger.error(f"提交个股资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_moneyflow_stock_dc_full_history_async(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD，默认 2023-09-11"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量历史同步个股资金流向（DC）数据（按股票代码逐只请求）

    采用逐只股票请求策略，避免单次6000行截断问题，支持中断续继。
    数据起始：20230911（DC 接口最早数据日期）
    积分消耗较高（5000积分/次），建议仅在初次建库或需要补全历史数据时使用。
    """
    try:
        from app.tasks.moneyflow_stock_dc_tasks import sync_moneyflow_stock_dc_full_history_task
        from app.services import TaskHistoryHelper
        from app.repositories.sync_config_repository import SyncConfigRepository

        start_date_formatted = start_date.replace('-', '') if start_date else None

        # 未传并发数时，从 sync_configs 读取配置值，兜底 5
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'moneyflow_stock_dc')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_moneyflow_stock_dc_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_moneyflow_stock_dc_full_history',
            display_name='个股资金流向（DC）全量历史同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted},
            source='moneyflow_stock_dc_page'
        )

        logger.info(f"个股资金流向（DC）全量历史同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="全量历史同步任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交个股资金流向（DC）全量历史同步任务失败: {e}")
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
