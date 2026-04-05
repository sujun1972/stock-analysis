"""
复权因子数据 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.adj_factor_service import AdjFactorService
from app.services.task_history_helper import TaskHistoryHelper
from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_adj_factor_data(
    ts_code: Optional[str] = Query(None, description="股票代码，如：000001.SZ"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, description="每页记录数"),
    page: int = Query(1, description="页码，从1开始")
):
    """
    查询复权因子数据

    Args:
        ts_code: 股票代码（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）
        limit: 每页记录数
        page: 页码

    Returns:
        复权因子数据列表
    """
    try:
        service = AdjFactorService()
        result = await service.get_adj_factor_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            page=page
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"查询复权因子数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码，如：000001.SZ"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取复权因子统计信息

    Args:
        ts_code: 股票代码（可选）
        start_date: 开始日期（可选）
        end_date: 结束日期（可选）

    Returns:
        统计信息
    """
    try:
        service = AdjFactorService()
        result = await service.get_statistics(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取复权因子统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_data(
    ts_code: Optional[str] = Query(None, description="股票代码，如：000001.SZ")
):
    """
    获取最新复权因子数据

    Args:
        ts_code: 股票代码（可选，如果不指定则返回最新日期的所有数据）

    Returns:
        最新复权因子数据
    """
    try:
        service = AdjFactorService()
        result = await service.get_latest_data(ts_code=ts_code)
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"获取最新复权因子数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_adj_factor_async(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：000001.SZ"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步复权因子数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    说明：
    - 可提取单只股票全部历史复权因子，也可以提取单日全部股票的复权因子
    - 更新时间：盘前9点15~20分完成当日复权因子入库
    - 积分要求：2000积分起，5000以上可高频调取

    Args:
        ts_code: 股票代码（可选）
        trade_date: 单个交易日期，格式：YYYY-MM-DD（可选）
        start_date: 开始日期，格式：YYYY-MM-DD（可选）
        end_date: 结束日期，格式：YYYY-MM-DD（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.adj_factor_tasks import sync_adj_factor_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_adj_factor_task.apply_async(
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
            task_name='tasks.sync_adj_factor',
            display_name='复权因子',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='adj_factor_page'
        )

        logger.info(f"复权因子同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交复权因子同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_adj_factor_full_history(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYYMMDD，默认 20210101"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量历史同步：逐只股票同步复权因子，8 并发，支持中断续继

    每只股票单独请求 Tushare，避免单次返回上限 6000 条的问题。
    支持 Redis 进度续继，任务中断后重新触发会自动跳过已完成股票。
    """
    try:
        from app.tasks.adj_factor_tasks import sync_adj_factor_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'adj_factor')
            concurrency = (cfg.get('full_sync_concurrency') or 8) if cfg else 8

        celery_task = sync_adj_factor_full_history_task.apply_async(
            kwargs={'start_date': start_date, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_adj_factor_full_history',
            display_name='复权因子（全量）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date, 'concurrency': concurrency},
            source='adj_factor_page'
        )

        logger.info(f"复权因子全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交复权因子全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
