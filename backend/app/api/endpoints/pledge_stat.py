"""
股权质押统计 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse
from app.services.pledge_stat_service import PledgeStatService
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_pledge_stat(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    min_pledge_ratio: Optional[float] = Query(None, description="最小质押比例"),
    limit: int = Query(30, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    获取股权质押统计数据

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）
        ts_code: 股票代码（可选）
        min_pledge_ratio: 最小质押比例（可选）
        limit: 返回记录数限制

    Returns:
        股权质押统计数据列表
    """
    try:
        service = PledgeStatService()
        result = await service.get_pledge_stat_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            min_pledge_ratio=min_pledge_ratio,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取股权质押统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取股权质押统计信息

    Args:
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）

    Returns:
        统计信息
    """
    try:
        service = PledgeStatService()
        stats = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(20, description="返回记录数限制")
):
    """
    获取最新的股权质押统计数据

    Args:
        ts_code: 股票代码（可选）
        limit: 返回记录数限制

    Returns:
        最新数据列表
    """
    try:
        service = PledgeStatService()
        result = await service.get_latest_data(ts_code=ts_code, limit=limit)
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-pledge")
async def get_high_pledge_stocks(
    end_date: Optional[str] = Query(None, description="截止日期，格式：YYYY-MM-DD，默认为最新日期"),
    min_ratio: float = Query(50.0, description="最小质押比例，默认50%"),
    limit: int = Query(100, description="返回记录数限制")
):
    """
    获取高质押比例股票

    Args:
        end_date: 截止日期（YYYY-MM-DD格式），默认为最新日期
        min_ratio: 最小质押比例（默认50%）
        limit: 返回记录数限制

    Returns:
        高质押比例股票列表
    """
    try:
        service = PledgeStatService()
        result = await service.get_high_pledge_stocks(
            end_date=end_date,
            min_ratio=min_ratio,
            limit=limit
        )
        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取高质押比例股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_pledge_stat_full_history(
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """逐只股票全量同步股权质押统计历史数据（支持中断续继）

    pledge_stat 接口只支持 ts_code + end_date，采用逐只股票请求方式，约5500只，5并发。
    """
    try:
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'pledge_stat')
        from app.tasks.pledge_stat_tasks import sync_pledge_stat_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'pledge_stat')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_pledge_stat_full_history_task.apply_async(kwargs={'concurrency': concurrency})

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_pledge_stat_full_history',
            display_name='股权质押统计（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'concurrency': concurrency},
            source='pledge_stat_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")
    except Exception as e:
        logger.error(f"提交股权质押统计全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_pledge_stat_async(
    trade_date: Optional[str] = Query(None, description="交易日期（截止日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步股权质押统计数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 截止日期，格式：YYYY-MM-DD
        ts_code: 股票代码（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.pledge_stat_tasks import sync_pledge_stat_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_pledge_stat_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'ts_code': ts_code
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_pledge_stat',
            display_name='股权质押统计',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'ts_code': ts_code
            },
            source='pledge_stat_page'
        )

        logger.info(f"股权质押统计同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交股权质押统计同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
