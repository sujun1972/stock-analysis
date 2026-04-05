"""
分红送股数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.dividend_service import DividendService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.models.user import User
from app.core.dependencies import require_admin

router = APIRouter()


@router.get("")
async def get_dividend(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(100, description="返回记录数限制"),
    offset: int = Query(0, description="偏移量（用于分页）")
):
    """
    查询分红送股数据

    Args:
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD（基于公告日期）
        end_date: 结束日期，格式：YYYY-MM-DD（基于公告日期）
        limit: 返回记录数限制
        offset: 偏移量（用于分页）
        current_user: 当前登录用户

    Returns:
        分红送股数据列表和统计信息
    """
    try:
        service = DividendService()
        result = await service.get_dividend_data(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return ApiResponse.success(data=result)
    except Exception as e:
        logger.error(f"查询分红送股数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_dividend_statistics(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取分红送股统计信息

    Args:
        ts_code: 股票代码
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户

    Returns:
        分红送股统计信息
    """
    try:
        service = DividendService()

        # 日期格式转换
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        statistics = await asyncio.to_thread(
            service.dividend_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            ts_code=ts_code
        )

        return ApiResponse.success(data=statistics)
    except Exception as e:
        logger.error(f"获取分红送股统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_dividend_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    record_date: Optional[str] = Query(None, description="股权登记日，格式：YYYY-MM-DD"),
    ex_date: Optional[str] = Query(None, description="除权除息日，格式：YYYY-MM-DD"),
    imp_ann_date: Optional[str] = Query(None, description="实施公告日，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步分红送股数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    注意：所有参数都是可选的。如果未提供任何参数，将使用最近交易日作为公告日期进行同步。

    Args:
        ts_code: 股票代码（可选）
        ann_date: 公告日期，格式：YYYY-MM-DD（可选）
        record_date: 股权登记日，格式：YYYY-MM-DD（可选）
        ex_date: 除权除息日，格式：YYYY-MM-DD（可选）
        imp_ann_date: 实施公告日，格式：YYYY-MM-DD（可选）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.dividend_tasks import sync_dividend_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        record_date_formatted = record_date.replace('-', '') if record_date else None
        ex_date_formatted = ex_date.replace('-', '') if ex_date else None
        imp_ann_date_formatted = imp_ann_date.replace('-', '') if imp_ann_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_dividend_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'record_date': record_date_formatted,
                'ex_date': ex_date_formatted,
                'imp_ann_date': imp_ann_date_formatted
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_dividend',
            display_name='分红送股数据',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'record_date': record_date_formatted,
                'ex_date': ex_date_formatted,
                'imp_ann_date': imp_ann_date_formatted
            },
            source='dividend_page'
        )

        logger.info(f"分红送股同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交分红送股同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history-async")
async def sync_dividend_full_history_async(
    start_date: Optional[str] = Query(None, description="起始日期（YYYYMMDD），不传则从系统配置读取"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """异步全量同步分红送股历史数据（按季度 period 切片 + Redis 续继）"""
    try:
        from app.tasks.dividend_tasks import sync_dividend_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'dividend')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_dividend_full_history_task.apply_async(
            kwargs={'start_date': start_date, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_dividend_full_history',
            display_name='分红送股全量同步',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date, 'concurrency': concurrency},
            source='dividend_page'
        )

        return ApiResponse.success(
            data=task_data,
            message="分红送股全量同步任务已提交，请在任务面板查看进度"
        )

    except Exception as e:
        logger.error(f"提交分红送股全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
