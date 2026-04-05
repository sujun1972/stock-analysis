"""
股东增减持API端点
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.core.dependencies import require_admin, get_current_user
from app.models.api_response import ApiResponse
from app.models.user import User
from app.services.stk_holdertrade_service import StkHoldertradeService
from app.services import TaskHistoryHelper

router = APIRouter()


@router.get("")
async def get_stk_holdertrade(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    holder_type: Optional[str] = Query(None, description="股东类型：G=高管 P=个人 C=公司"),
    trade_type: Optional[str] = Query(None, description="交易类型：IN=增持 DE=减持"),
    limit: int = Query(100, description="返回记录数"),
    offset: int = Query(0, description="偏移量")
):
    """
    查询股东增减持数据

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码
        holder_type: 股东类型：G=高管 P=个人 C=公司
        trade_type: 交易类型：IN=增持 DE=减持
        limit: 返回记录数
        offset: 偏移量

    Returns:
        股东增减持数据列表和统计信息
    """
    try:
        service = StkHoldertradeService()
        result = await service.get_stk_holdertrade_data(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            holder_type=holder_type,
            trade_type=trade_type,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询股东增减持数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="股票代码")
):
    """
    获取股东增减持统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        ts_code: 股票代码

    Returns:
        统计信息
    """
    try:
        service = StkHoldertradeService()
        statistics = await service.get_statistics(
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )

        return ApiResponse.success(data=statistics)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新数据信息

    Returns:
        最新公告日期和记录数
    """
    try:
        service = StkHoldertradeService()
        latest = await service.get_latest_data()

        return ApiResponse.success(data=latest)

    except Exception as e:
        logger.error(f"获取最新数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-full-history")
async def sync_stk_holdertrade_full_history(
    start_date: Optional[str] = Query(None, description="起始日期，格式：YYYY-MM-DD，不传则从2009年开始"),
    concurrency: Optional[int] = Query(None, ge=1, le=20, description="并发数，不传则从 sync_configs 读取"),
    current_user: User = Depends(require_admin)
):
    """按年切片全量同步股东增减持历史数据（支持中断续继）"""
    try:
        from app.tasks.stk_holdertrade_tasks import sync_stk_holdertrade_full_history_task
        from app.repositories.sync_config_repository import SyncConfigRepository

        start_date_formatted = start_date.replace('-', '') if start_date else None

        # 未传并发数时，从 sync_configs 读取，兜底默认值
        if concurrency is None:
            sync_config_repo = SyncConfigRepository()
            cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'stk_holdertrade')
            concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5

        celery_task = sync_stk_holdertrade_full_history_task.apply_async(
            kwargs={'start_date': start_date_formatted, 'concurrency': concurrency}
        )

        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_holdertrade_full_history',
            display_name='股东增减持（全量历史）',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={'start_date': start_date_formatted, 'concurrency': concurrency},
            source='stk_holdertrade_page'
        )

        return ApiResponse.success(data=task_data, message="全量同步任务已提交")
    except Exception as e:
        logger.error(f"提交股东增减持全量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    ann_date: Optional[str] = Query(None, description="公告日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    trade_type: Optional[str] = Query(None, description="交易类型：IN=增持 DE=减持"),
    holder_type: Optional[str] = Query(None, description="股东类型：G=高管 P=个人 C=公司"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步股东增减持数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码
        ann_date: 公告日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        trade_type: 交易类型：IN=增持 DE=减持
        holder_type: 股东类型：G=高管 P=个人 C=公司
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.stk_holdertrade_tasks import sync_stk_holdertrade_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        ann_date_formatted = ann_date.replace('-', '') if ann_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_stk_holdertrade_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'trade_type': trade_type,
                'holder_type': holder_type
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_stk_holdertrade',
            display_name='股东增减持',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'ts_code': ts_code,
                'ann_date': ann_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'trade_type': trade_type,
                'holder_type': holder_type
            },
            source='stk_holdertrade_page'
        )

        logger.info(f"股东增减持同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交股东增减持同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
