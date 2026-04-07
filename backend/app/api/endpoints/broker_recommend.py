"""
券商每月荐股 API 端点

提供券商月度金股推荐数据的查询和同步功能
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.broker_recommend_service import BrokerRecommendService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_broker_recommend(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM"),
    start_month: Optional[str] = Query(None, description="开始月度,格式:YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度,格式:YYYY-MM"),
    broker: Optional[str] = Query(None, description="券商名称"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=1000),
    limit: Optional[int] = Query(None, description="返回记录数（兼容旧参数）", ge=1, le=1000)
):
    """
    查询券商荐股数据

    Args:
        month: 单个月度,格式：YYYY-MM
        start_month: 开始月度,格式：YYYY-MM
        end_month: 结束月度,格式：YYYY-MM
        broker: 券商名称（可选）
        ts_code: 股票代码（可选）
        page: 页码
        page_size: 每页记录数
        limit: 返回记录数（兼容旧参数）

    Returns:
        券商荐股数据列表
    """
    try:
        actual_limit = limit if limit is not None else page_size
        actual_offset = (page - 1) * page_size if limit is None else 0

        service = BrokerRecommendService()

        # 转换日期格式：YYYY-MM -> YYYYMM
        month_fmt = month.replace('-', '') if month else None
        start_month_fmt = start_month.replace('-', '') if start_month else None
        end_month_fmt = end_month.replace('-', '') if end_month else None

        result = await service.get_broker_recommend_data(
            month=month_fmt,
            start_month=start_month_fmt,
            end_month=end_month_fmt,
            broker=broker,
            ts_code=ts_code,
            limit=actual_limit,
            offset=actual_offset
        )

        # 格式化返回数据（YYYYMM -> YYYY-MM）
        for item in result['items']:
            if item['month']:
                item['month'] = f"{item['month'][:4]}-{item['month'][4:]}"

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询券商荐股数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_month: Optional[str] = Query(None, description="开始月度,格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度,格式：YYYY-MM")
):
    """
    获取券商荐股统计信息

    Args:
        start_month: 开始月度（可选）
        end_month: 结束月度（可选）

    Returns:
        统计信息
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        start_month_fmt = start_month.replace('-', '') if start_month else None
        end_month_fmt = end_month.replace('-', '') if end_month else None

        stats = await service.get_statistics(
            start_month=start_month_fmt,
            end_month=end_month_fmt
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取券商荐股统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新月度数据

    Returns:
        最新月度及数据
    """
    try:
        service = BrokerRecommendService()

        # 获取最新月度
        latest_month = await service.get_latest_month()
        if not latest_month:
            return ApiResponse.success(data={
                "latest_month": None,
                "items": [],
                "total": 0
            })

        # 格式化月度（YYYYMM -> YYYY-MM）
        latest_month_formatted = f"{latest_month[:4]}-{latest_month[4:]}"

        # 获取最新月度的数据
        result = await service.get_broker_recommend_data(
            month=latest_month,
            limit=100
        )

        # 格式化返回数据
        for item in result['items']:
            if item['month']:
                item['month'] = f"{item['month'][:4]}-{item['month'][4:]}"

        return ApiResponse.success(data={
            "latest_month": latest_month_formatted,
            "items": result['items'],
            "total": result['total']
        })

    except Exception as e:
        logger.error(f"获取最新月度数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brokers")
async def get_broker_list(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM")
):
    """
    获取券商列表

    Args:
        month: 月度（可选）

    Returns:
        券商名称列表
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        month_fmt = month.replace('-', '') if month else None

        brokers = await service.get_broker_list(month=month_fmt)

        return ApiResponse.success(data={"brokers": brokers})

    except Exception as e:
        logger.error(f"获取券商列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-stocks")
async def get_top_stocks(
    month: str = Query(..., description="月度,格式：YYYY-MM"),
    limit: int = Query(20, description="返回数量")
):
    """
    获取某月被推荐次数最多的股票

    Args:
        month: 月度,格式：YYYY-MM（必需）
        limit: 返回数量

    Returns:
        热门股票列表
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        month_fmt = month.replace('-', '')

        stocks = await service.get_top_stocks(
            month=month_fmt,
            limit=limit
        )

        return ApiResponse.success(data={"stocks": stocks})

    except Exception as e:
        logger.error(f"获取热门股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest-start-date")
async def get_suggest_start_date(
    _current_user: User = Depends(require_admin)
):
    """返回增量同步的建议起始月度（YYYYMM）。"""
    service = BrokerRecommendService()
    suggested = await service.get_suggested_start_date()
    return ApiResponse.success(data={"suggested_start_date": suggested})


@router.post("/sync-async")
async def sync_broker_recommend_async(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM"),
    current_user: User = Depends(require_admin)
):
    """异步同步券商荐股数据（通过Celery任务）"""
    try:
        from app.tasks.broker_recommend_tasks import sync_broker_recommend_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 转换日期格式：YYYY-MM -> YYYYMM
        month_formatted = month.replace('-', '') if month else None

        # 从 sync_configs 读取限速配置
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'broker_recommend')
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_broker_recommend_task.apply_async(
            kwargs={
                'month': month_formatted,
                'max_requests_per_minute': max_rpm,
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_broker_recommend',
            display_name='券商每月荐股',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'month': month_formatted
            },
            source='broker_recommend_page'
        )

        logger.info(f"券商荐股同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="任务已提交，正在后台执行")

    except Exception as e:
        logger.error(f"提交券商荐股同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_broker_recommend_full_history(
    start_date: Optional[str] = Query(None, description="起始月份，格式：YYYYMM 或 YYYY-MM（不传则从 200801 开始）"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """全量同步券商荐股历史数据（逐月请求，Redis Set 续继）"""
    try:
        from app.tasks.broker_recommend_tasks import sync_broker_recommend_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository
        from app.api.endpoints.sync_dashboard import release_stale_lock

        await asyncio.to_thread(release_stale_lock, 'broker_recommend')

        # broker_recommend 使用月份格式，取前6位（YYYYMM）
        start_date_formatted = start_date.replace('-', '')[:6] if start_date else None
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'broker_recommend')
        if concurrency is None:
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        strategy = (cfg.get('full_sync_strategy') or 'by_month_str') if cfg else 'by_month_str'
        max_rpm = cfg.get('max_requests_per_minute') if cfg else None

        celery_task = sync_broker_recommend_full_history_task.apply_async(
            kwargs={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
                'max_requests_per_minute': max_rpm,
            }
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_broker_recommend_full_history',
            display_name='券商荐股全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'start_date': start_date_formatted,
                'concurrency': concurrency,
                'strategy': strategy,
            },
            source='broker_recommend_page'
        )

        logger.info(f"券商荐股全量同步任务已提交: {celery_task.id}")
        return ApiResponse.success(data=task_data, message="全量同步任务已提交")

    except Exception as e:
        logger.error(f"提交券商荐股全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
