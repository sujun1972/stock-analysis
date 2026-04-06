"""
每日涨跌停价格 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.stk_limit_d_service import StkLimitDService
from app.services import TaskHistoryHelper
from app.models.user import User
from app.core.dependencies import require_admin
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_stk_limit_d(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(30, ge=1, le=200, description="每页记录数，默认30")
):
    """
    查询每日涨跌停价格数据（支持分页）

    Args:
        ts_code: 股票代码（可选）
        start_date: 开始日期，格式：YYYY-MM-DD（可选）
        end_date: 结束日期，格式：YYYY-MM-DD（可选）
        page: 页码（从1开始）
        page_size: 每页记录数

    Returns:
        每日涨跌停价格数据、统计信息和总记录数
    """
    try:
        service = StkLimitDService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        result = await service.get_stk_limit_d_data(
            ts_code=ts_code,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            page=page,
            page_size=page_size
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取每日涨跌停价格数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_stk_limit_d(
    limit: int = Query(100, description="返回记录数限制，默认100")
):
    """
    获取最新的每日涨跌停价格数据

    Args:
        limit: 返回记录数限制

    Returns:
        最新的每日涨跌停价格数据
    """
    try:
        service = StkLimitDService()
        result = await service.get_latest_data(limit=limit)

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新每日涨跌停价格数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_stk_limit_d_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取每日涨跌停价格统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD（可选）
        end_date: 结束日期，格式：YYYY-MM-DD（可选）
        ts_code: 股票代码（可选）

    Returns:
        统计信息
    """
    try:
        service = StkLimitDService()

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        statistics = await service.get_statistics(
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            ts_code=ts_code
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取每日涨跌停价格统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_stk_limit_d_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步每日涨跌停价格数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可选）
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_limit_d_tasks import sync_stk_limit_d_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        celery_task = sync_stk_limit_d_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_limit_d',
            display_name='每日涨跌停价格',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='stk_limit_d_page'
        )

        logger.info(f"每日涨跌停价格同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交每日涨跌停价格同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_stk_limit_d_full_history(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYYMMDD，默认 20210101"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """
    全量历史同步：逐只股票同步每日涨跌停价格，3 并发，支持中断续继

    每只股票单独请求 Tushare，避免单次返回上限 5800 条的问题。
    支持 Redis 进度续继，任务中断后重新触发会自动跳过已完成股票。
    """
    try:
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'stk_limit_d')
        from app.tasks.stk_limit_d_tasks import sync_stk_limit_d_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'stk_limit_d')
            concurrency = (cfg.get('full_sync_concurrency') or 3) if cfg else 3

        celery_task = sync_stk_limit_d_full_history_task.apply_async(
            kwargs={'start_date': start_date, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_limit_d_full_history',
            display_name='每日涨跌停价格（全量）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date, 'concurrency': concurrency},
            source='stk_limit_d_page'
        )

        logger.info(f"每日涨跌停价格全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交每日涨跌停价格全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
