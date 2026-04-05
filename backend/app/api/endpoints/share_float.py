"""
限售股解禁 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.share_float_service import ShareFloatService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin, get_current_user
from app.models.user import User


router = APIRouter()


@router.get("")
async def get_share_float(
    start_date: Optional[str] = Query(None, description="开始日期（解禁日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（解禁日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    float_date: Optional[str] = Query(None, description="解禁日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量")
):
    """
    查询限售股解禁数据

    Args:
        start_date: 开始日期（解禁日期），格式：YYYY-MM-DD
        end_date: 结束日期（解禁日期），格式：YYYY-MM-DD
        ts_code: 股票代码
        ann_date: 公告日期，格式：YYYY-MM-DD
        float_date: 解禁日期，格式：YYYY-MM-DD
        limit: 返回记录数限制

    Returns:
        限售股解禁数据列表
    """
    try:
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        float_date_formatted = float_date.replace('-', '') if float_date else None

        service = ShareFloatService()
        result = await service.get_share_float_data(
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            ts_code=ts_code,
            ann_date=ann_date_formatted,
            float_date=float_date_formatted,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询限售股解禁数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期（解禁日期），格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期（解禁日期），格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取限售股解禁统计信息

    Args:
        start_date: 开始日期（解禁日期），格式：YYYY-MM-DD
        end_date: 结束日期（解禁日期），格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        service = ShareFloatService()
        result = await service.get_statistics(
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            ts_code=ts_code
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取限售股解禁统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest(
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取最新的限售股解禁数据

    Args:
        ts_code: 股票代码

    Returns:
        最新数据
    """
    try:
        service = ShareFloatService()
        result = await service.get_latest_data(ts_code=ts_code)

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取最新限售股解禁数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_share_float_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD，不传则从2005年开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """按年切片全量同步限售股解禁历史数据（支持中断续继）"""
    try:
        from app.tasks.share_float_tasks import sync_share_float_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        start_date_formatted = start_date.replace('-', '') if start_date else None

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'share_float')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_share_float_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_share_float_full_history',
            display_name='限售股解禁（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
            source='share_float_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")
    except Exception as e:
        logger.error(f"提交限售股解禁全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_share_float_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    float_date: Optional[str] = Query(None, description="解禁日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="解禁开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="解禁结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步限售股解禁数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码
        ann_date: 公告日期，格式：YYYY-MM-DD
        float_date: 解禁日期，格式：YYYY-MM-DD
        start_date: 解禁开始日期，格式：YYYY-MM-DD
        end_date: 解禁结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.share_float_tasks import sync_share_float_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ts_code_formatted = ts_code
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        float_date_formatted = float_date.replace('-', '') if float_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_share_float_task.apply_async(
            kwargs={
                'ts_code': ts_code_formatted,
                'ann_date': ann_date_formatted,
                'float_date': float_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_share_float',
            display_name='限售股解禁',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code_formatted,
                'ann_date': ann_date_formatted,
                'float_date': float_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
            },
            source='share_float_page'
        )

        logger.info(f"限售股解禁同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交限售股解禁同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
