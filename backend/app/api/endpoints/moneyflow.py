"""
个股资金流向API（Tushare标准接口）

提供基于主动买卖单统计的资金流向数据接口，包含小单、中单、大单、特大单的买卖量和买卖额，
支持查询历史数据、同步最新数据、获取资金流入排名等功能。

数据源：Tushare pro.moneyflow()
积分消耗：2000积分/次
单次限制：最大6000行
"""

import asyncio
import json
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
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user)
):
    """
    获取个股资金流向数据（Tushare标准接口）

    基于主动买卖单统计，包含小单/中单/大单/特大单的买卖量和买卖额

    Returns:
        包含资金流向数据的响应
    """
    try:
        service = MoneyflowService()
        result = await asyncio.to_thread(
            service.get_moneyflow_data,
            ts_code=ts_code,
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
        from src.database.db_manager import DatabaseManager

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

        # 记录任务到celery_task_history表，用于任务面板显示
        db_manager = DatabaseManager()
        history_query = """
            INSERT INTO celery_task_history
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        task_params = {
            'ts_code': ts_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }

        task_metadata = {
            "trigger": "manual",
            "source": "moneyflow_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_moneyflow',
                '个股资金流向（Tushare）',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"个股资金流向同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_moneyflow",
                "display_name": "个股资金流向（Tushare）",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交个股资金流向同步任务失败: {e}")
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
