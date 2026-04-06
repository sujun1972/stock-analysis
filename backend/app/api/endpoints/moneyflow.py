"""
个股资金流向API（Tushare标准接口）

提供基于主动买卖单统计的资金流向数据接口，包含小单、中单、大单、特大单的买卖量和买卖额，
支持查询历史数据、同步最新数据、获取资金流入排名等功能。

数据源：Tushare pro.moneyflow()
积分消耗：2000积分/次
单次限制：最大6000行
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from loguru import logger

from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.moneyflow_service import MoneyflowService

router = APIRouter()


@router.get("")
async def get_moneyflow(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="单日交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取个股资金流向数据（Tushare标准接口）

    基于主动买卖单统计，包含小单/中单/大单/特大单的买卖量和买卖额

    Returns:
        包含资金流向数据和回填交易日期的响应
    """
    try:
        service = MoneyflowService()
        result = await asyncio.to_thread(
            service.get_moneyflow_data,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(
            data=result,
            message="获取个股资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    同步个股资金流向数据（管理员功能）

    同步模式：阻塞式，等待完成后返回结果
    """
    try:
        from app.services.extended_sync_service import ExtendedDataSyncService

        service = ExtendedDataSyncService()

        # 转换日期格式
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 执行同步
        result = await service.sync_moneyflow(
            ts_code=ts_code,
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        if result["status"] == "success":
            return ApiResponse.success(
                data=result,
                message=f"成功同步 {result['records']} 条个股资金流向数据"
            )
        else:
            return ApiResponse.error(
                message=result.get("error", "同步失败")
            )

    except Exception as e:
        logger.error(f"同步个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步个股资金流向数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可选，不指定则获取活跃股票）
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应

    注意：
        - 积分消耗：2000积分/次
        - 单次最大6000行记录
        - 股票和时间参数至少输入一个
    """
    try:
        from app.tasks.moneyflow_tasks import sync_moneyflow_task
        from app.services import TaskHistoryHelper

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_moneyflow_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'stock_list': None
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_moneyflow',
            display_name='个股资金流向（Tushare）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='moneyflow_page'
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
async def sync_moneyflow_full_history_async(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD，默认 2010-01-01"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量历史同步个股资金流向数据（按股票代码逐只请求）

    采用逐只股票请求策略，避免单次6000行截断问题，支持中断续继。
    积分消耗较高，建议仅在初次建库或需要补全历史数据时使用。
    """
    try:
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'moneyflow')
        from app.tasks.moneyflow_tasks import sync_moneyflow_full_history_task
        from app.services import TaskHistoryHelper
        from app.repositories.sync_config_repository import SyncConfigRepository

        start_date_formatted = start_date.replace('-', '') if start_date else None

        # 未传并发数时，从 sync_configs 读取配置值，兜底 5
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'moneyflow')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_moneyflow_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_moneyflow_full_history',
            display_name='个股资金流向全量历史同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted},
            source='moneyflow_page'
        )

        logger.info(f"个股资金流向全量历史同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="全量历史同步任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交个股资金流向全量历史同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_moneyflow_stocks(
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(get_current_user)
):
    """
    获取资金净流入排名前N的股票（默认最新交易日）

    基于净流入额排序
    """
    try:
        service = MoneyflowService()
        result = await asyncio.to_thread(
            service.get_top_stocks,
            trade_date=trade_date,
            limit=limit
        )

        return ApiResponse.success(
            data=result,
            message="获取资金流入排名成功"
        )

    except Exception as e:
        logger.error(f"获取资金流入排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
