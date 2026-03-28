"""
沪深港股通持股明细数据 API 端点
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.services.hk_hold_service import HkHoldService
from app.services import TaskHistoryHelper
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_hk_hold(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    ts_code: Optional[str] = Query(None, description="A股代码（如 600000.SH）"),
    code: Optional[str] = Query(None, description="港股代码（如 00700.HK）"),
    exchange: Optional[str] = Query(None, description="交易所类型（SH/SZ/HK）"),
    sort_by: Optional[str] = Query(None, description="排序字段（ratio/vol/amount/trade_date）"),
    sort_order: str = Query('desc', description="排序方向（asc/desc）"),
    page: int = Query(1, description="页码", ge=1),
    page_size: int = Query(100, description="每页记录数", ge=1, le=500)
):
    """
    查询沪深港股通持股明细数据（支持分页和排序）

    说明：交易所于从2024年8月20开始停止发布日度北向资金数据，改为季度披露

    Returns:
        沪深港股通持股明细数据列表、分页信息、统计信息和默认日期
    """
    try:
        service = HkHoldService()

        # 若未传日期，解析最近有数据的交易日并回传给前端（用于日期选择器自动回填）
        resolved_date = None
        if not trade_date:
            resolved_date = await service.resolve_default_trade_date()
            trade_date = resolved_date

        result = await service.get_hk_hold_data(
            trade_date=trade_date,
            ts_code=ts_code,
            code=code,
            exchange=exchange,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )

        # 回传解析出的日期，供前端回填日期选择器
        result['trade_date'] = trade_date

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询沪深港股通持股明细数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD")
):
    """
    获取沪深港股通持股明细数据统计信息
    """
    try:
        service = HkHoldService()
        result = await service.get_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步沪深港股通持股明细数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    不传日期时，Service 层自动使用最近30天范围。

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.hk_hold_tasks import sync_hk_hold_task

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_hk_hold_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
            }
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_hk_hold',
            display_name='沪深港股通持股明细',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
            },
            source='hk_hold_page'
        )

        logger.info(f"沪深港股通持股明细数据同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提交沪深港股通持股明细数据同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
