"""
财务指标数据 API 端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.core.dependencies import require_admin
from app.models.user import User
from app.services.fina_indicator_service import FinaIndicatorService
from app.models.api_response import ApiResponse
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_fina_indicator(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD（如2023-12-31表示年报）"),
    limit: int = Query(30, description="限制返回数量，默认30"),
    offset: int = Query(0, description="偏移量（用于分页）")
):
    """
    查询财务指标数据

    财务指标包括150+指标，如EPS、ROE、资产负债率、毛利率等
    """
    try:
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None
        period_formatted = period.replace('-', '') if period else None

        service = FinaIndicatorService()
        result = await service.get_fina_indicator_data(
            ts_code=ts_code,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            period=period_formatted,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询财务指标数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取财务指标统计信息
    """
    try:
        # 日期格式转换
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        service = FinaIndicatorService()
        statistics = await service.get_statistics(
            ts_code=ts_code,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取财务指标统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_fina_indicator(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(30, description="限制返回数量")
):
    """
    获取最新财务指标数据（按公告日期排序）
    """
    try:
        service = FinaIndicatorService()
        result = await service.get_fina_indicator_data(
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新财务指标数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_fina_indicator_async(
    ts_code: Optional[str] = Query(None, description="股票代码，格式：TSXXXXXX.XX"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="报告期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步财务指标数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    注意：
    - 每次请求最多返回100条记录（Tushare限制）
    - 积分消耗：2000分/次
    - 建议按股票代码或报告期分批同步

    Args:
        ts_code: 股票代码，格式：TSXXXXXX.XX
        ann_date: 公告日期，格式：YYYY-MM-DD
        start_date: 开始日期（报告期），格式：YYYY-MM-DD
        end_date: 结束日期（报告期），格式：YYYY-MM-DD
        period: 报告期，格式：YYYY-MM-DD（如2023-12-31表示年报）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.fina_indicator_tasks import sync_fina_indicator_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None
        period_formatted = period.replace('-', '') if period else None

        # 提交Celery任务（异步执行）
        celery_task = sync_fina_indicator_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_fina_indicator',
            display_name='财务指标',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'period': period_formatted
            },
            source='fina_indicator_page'
        )

        logger.info(f"财务指标同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交财务指标同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_fina_indicator_full_history_async(
    start_date: Optional[str] = Query(None, description="起始日期（YYYYMMDD），不传则从系统配置读取"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """异步全量同步财务指标历史数据（按季度 period 切片 + Redis 续继）"""
    try:
        from app.api.endpoints.sync_dashboard import release_stale_lock
        await asyncio.to_thread(release_stale_lock, 'fina_indicator')
        from app.tasks.fina_indicator_tasks import sync_fina_indicator_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'fina_indicator')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_fina_indicator_full_history_task.apply_async(
            kwargs={'start_date': start_date, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_fina_indicator_full_history',
            display_name='财务指标全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date, 'concurrency': concurrency},
            source='fina_indicator_page'
        )

        return ApiResponse.success(
            data=task_data,
            message="财务指标全量同步任务已提交，请在任务面板查看进度"
        )

    except Exception as e:
        logger.error(f"提交财务指标全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
