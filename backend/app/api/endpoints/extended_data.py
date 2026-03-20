"""
扩展数据API端点
提供Tushare扩展数据的查询和同步接口

重构说明：
- 移除了所有直接的 SQL 查询
- 使用 Service 层处理业务逻辑
- 符合三层架构规范（API -> Service -> Repository）
"""

import asyncio
from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import date, datetime

from app.core.dependencies import get_current_user
from app.models.api_response import ApiResponse
from app.services import (
    DailyBasicService,
    HkHoldService,
    StkLimitService,
    BlockTradeService,
    MoneyflowService,
    MarginDetailService
)
from loguru import logger
from app.tasks.extended_sync_tasks import (
    sync_daily_basic_task,
    sync_moneyflow_task,
    sync_hk_hold_task,
    sync_margin_task,
    sync_stk_limit_task,
    sync_block_trade_task
)

router = APIRouter(tags=["extended_data"])


@router.get("/daily-basic/{ts_code}")
async def get_daily_basic(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=1000, description="返回记录数")
):
    """
    获取股票每日指标
    - 换手率、市盈率、市净率等
    - 用于短线选股和风险评估
    """
    try:
        # 使用 Service 层
        service = DailyBasicService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None

        # 调用 Service 查询
        result = await service.get_daily_basic_data(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取每日指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moneyflow/{ts_code}")
def get_moneyflow(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=500, description="返回记录数")
):
    """
    获取个股资金流向
    - 大单、中单、小单资金流向
    - 判断主力资金动向
    """
    try:
        # 使用 Service 层
        service = MoneyflowService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None

        # 调用 Service 查询
        result = service.get_moneyflow_data(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )

        return {
            "code": 0,
            "data": result["items"],
            "count": result["total"],
            "msg": "success"
        }

    except Exception as e:
        logger.error(f"获取资金流向失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hk-hold")
async def get_hk_hold(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    exchange: Optional[str] = Query(None, description="交易所：SH/SZ"),
    top: int = Query(50, le=200, description="返回前N条")
):
    """
    获取北向资金持股数据
    - 沪股通、深股通持股
    - 外资动向重要参考
    """
    try:
        # 使用 Service 层
        service = HkHoldService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        trade_date_str = trade_date.strftime("%Y-%m-%d") if trade_date else None

        # 调用 Service 查询
        result = await service.get_hk_hold_data(
            trade_date=trade_date_str,
            exchange=exchange,
            limit=top
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取北向资金失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/margin/{ts_code}")
async def get_margin_detail(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=500, description="返回记录数")
):
    """
    获取融资融券数据
    - 两融余额变化
    - 市场情绪指标
    """
    try:
        # 使用 Service 层
        service = MarginDetailService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        start_date_str = start_date.strftime("%Y-%m-%d") if start_date else None
        end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None

        # 调用 Service 查询
        result = await service.get_margin_detail_data(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )

        return {
            "code": 0,
            "data": result["data"],
            "count": len(result["data"]),
            "msg": "success"
        }

    except Exception as e:
        logger.error(f"获取融资融券数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limit-prices")
async def get_limit_prices(
    trade_date: date = Query(..., description="交易日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, le=5000, description="返回记录数")
):
    """
    获取涨跌停价格
    - 当日所有股票的涨跌停价格
    - 用于交易参考
    """
    try:
        # 使用 Service 层
        service = StkLimitService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        trade_date_str = trade_date.strftime("%Y-%m-%d")

        # 调用 Service 查询
        result = await service.get_stk_limit_data(
            trade_date=trade_date_str,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取涨跌停价格失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/block-trade")
async def get_block_trade(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, le=500, description="返回记录数")
):
    """
    获取大宗交易数据
    - 机构大额交易
    - 判断机构动向
    """
    try:
        # 使用 Service 层
        service = BlockTradeService()

        # 转换日期格式 (date -> YYYY-MM-DD)
        trade_date_str = trade_date.strftime("%Y-%m-%d") if trade_date else None

        # 调用 Service 查询
        result = await service.get_block_trade_data(
            trade_date=trade_date_str,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"获取大宗交易数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/trigger")
def trigger_sync(
    data_type: str = Query(..., description="数据类型：daily_basic|moneyflow|hk_hold|margin|stk_limit|block_trade"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYYMMDD"),
    _: dict = Depends(get_current_user)
):
    """
    手动触发数据同步
    需要管理员权限
    """

    task_map = {
        "daily_basic": sync_daily_basic_task,
        "moneyflow": sync_moneyflow_task,
        "hk_hold": sync_hk_hold_task,
        "margin": sync_margin_task,
        "stk_limit": sync_stk_limit_task,
        "block_trade": sync_block_trade_task
    }

    if data_type not in task_map:
        raise HTTPException(status_code=400, detail="不支持的数据类型")

    task = task_map[data_type]
    result = task.delay(trade_date=trade_date)

    return {
        "code": 0,
        "data": {
            "task_id": result.id,
            "data_type": data_type,
            "trade_date": trade_date
        },
        "msg": "同步任务已提交"
    }


@router.get("/sync/status/{task_id}")
def get_sync_status(task_id: str):
    """
    获取同步任务状态
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "code": 0,
        "data": {
            "task_id": task_id,
            "state": result.state,
            "result": result.result if result.state == "SUCCESS" else None,
            "info": result.info if result.state == "PENDING" else None
        },
        "msg": "success"
    }


@router.get("/stats/summary")
async def get_data_summary():
    """
    获取扩展数据统计摘要

    使用 asyncio.gather 并发获取多个统计数据，提高性能
    """
    try:
        # 使用 Service 层获取统计信息
        daily_basic_service = DailyBasicService()
        moneyflow_service = MoneyflowService()
        hk_hold_service = HkHoldService()
        margin_detail_service = MarginDetailService()

        # 并发获取所有统计数据
        stats_results = await asyncio.gather(
            daily_basic_service.get_statistics(),
            moneyflow_service.get_statistics(),
            hk_hold_service.get_statistics(),
            margin_detail_service.get_statistics()
        )

        stats = {
            'daily_basic': stats_results[0],
            'moneyflow': stats_results[1],
            'hk_hold': stats_results[2],
            'margin_detail': stats_results[3]
        }

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取数据统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))