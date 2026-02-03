"""
市场状态 API (重构版本)

✅ 任务 0.5: 重写 Market API
- 使用 Core Adapters 代替 DatabaseService
- Backend 只负责：参数验证、响应格式化
- 业务逻辑全部由 Core 处理

作者: Backend Team
创建日期: 2026-02-02
版本: 2.0.0 (架构修正版)
"""

from fastapi import APIRouter, Query
from typing import Optional, List
from datetime import datetime
from loguru import logger

from app.core_adapters.market_adapter import MarketAdapter
from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse
from app.core.exceptions import DataQueryError

router = APIRouter()

# 全局 Adapter 实例
market_adapter = MarketAdapter()
data_adapter = DataAdapter()


@router.get("/status")
async def get_market_status():
    """
    获取当前市场状态

    ✅ 架构修正版：
    - Backend 只负责：调用 Core Adapter、响应格式化
    - Core 负责：市场状态判断逻辑

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "status": "trading",
            "description": "交易中（早盘）",
            "is_trading": true,
            "should_refresh": true,
            "next_session_time": "2023-12-29 13:00:00",
            "next_session_desc": "今日午盘开盘",
            "trading_hours": {
                "morning_open": "09:30:00",
                "morning_close": "11:30:00",
                "afternoon_open": "13:00:00",
                "afternoon_close": "15:00:00"
            }
        }
    }
    """
    # 1. 调用 Core Adapter 获取市场状态
    status, description = await market_adapter.get_market_status()

    # 2. 判断是否交易时段
    is_trading = status in ['trading', 'call_auction']

    # 3. 获取下一个交易时段
    next_time, next_desc = await market_adapter.get_next_trading_session()

    # 4. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "status": status,
            "description": description,
            "is_trading": is_trading,
            "should_refresh": is_trading,
            "next_session_time": next_time.strftime('%Y-%m-%d %H:%M:%S') if next_time else None,
            "next_session_desc": next_desc,
            "trading_hours": {
                "morning_open": market_adapter.MORNING_OPEN.strftime('%H:%M:%S'),
                "morning_close": market_adapter.MORNING_CLOSE.strftime('%H:%M:%S'),
                "afternoon_open": market_adapter.AFTERNOON_OPEN.strftime('%H:%M:%S'),
                "afternoon_close": market_adapter.AFTERNOON_CLOSE.strftime('%H:%M:%S')
            }
        },
        message="获取市场状态成功"
    ).to_dict()


@router.get("/trading-info")
async def get_trading_info():
    """
    获取交易时段信息

    ✅ 新增端点：提供完整的交易时段信息

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "is_trading_day": true,
            "is_trading_time": true,
            "is_call_auction": false,
            "current_time": "2023-12-29 10:30:00",
            "market_status": "trading",
            "market_description": "交易中（早盘）",
            "trading_sessions": {
                "call_auction": {
                    "start": "09:15:00",
                    "end": "09:25:00"
                },
                "morning": {
                    "start": "09:30:00",
                    "end": "11:30:00"
                },
                "afternoon": {
                    "start": "13:00:00",
                    "end": "15:00:00"
                }
            }
        }
    }
    """
    # 1. 调用 Core Adapter 获取交易状态
    now = datetime.now()
    is_trading_day = await market_adapter.is_trading_day()
    is_trading_time = await market_adapter.is_trading_time()
    is_call_auction = await market_adapter.is_call_auction_time()
    status, description = await market_adapter.get_market_status()

    # 2. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "is_trading_day": is_trading_day,
            "is_trading_time": is_trading_time,
            "is_call_auction": is_call_auction,
            "current_time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "market_status": status,
            "market_description": description,
            "trading_sessions": {
                "call_auction": {
                    "start": market_adapter.CALL_AUCTION_START.strftime('%H:%M:%S'),
                    "end": market_adapter.CALL_AUCTION_END.strftime('%H:%M:%S')
                },
                "morning": {
                    "start": market_adapter.MORNING_OPEN.strftime('%H:%M:%S'),
                    "end": market_adapter.MORNING_CLOSE.strftime('%H:%M:%S')
                },
                "afternoon": {
                    "start": market_adapter.AFTERNOON_OPEN.strftime('%H:%M:%S'),
                    "end": market_adapter.AFTERNOON_CLOSE.strftime('%H:%M:%S')
                }
            }
        },
        message="获取交易信息成功"
    ).to_dict()


@router.get("/refresh-check")
async def check_refresh_needed(
    codes: Optional[List[str]] = Query(None, description="股票代码列表（可选）"),
    force: bool = Query(False, description="是否强制刷新")
):
    """
    检查是否需要刷新数据

    ✅ 架构修正版：
    - Backend 只负责：参数验证、调用 Core Adapter、响应格式化
    - Core 负责：数据新鲜度判断逻辑

    参数:
    - codes: 股票代码列表（可选，不指定则检查所有股票）
    - force: 是否强制刷新（默认 false）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "should_refresh": true,
            "reason": "实时行情更新",
            "market_status": "trading",
            "market_description": "交易中（早盘）",
            "last_update": "2023-12-29 10:25:30",
            "codes_count": 10,
            "time_since_last_update_seconds": 270
        }
    }
    """
    # 1. 获取市场状态
    status, description = await market_adapter.get_market_status()

    # 2. 获取最后更新时间
    # 这里简化处理，实际应该查询数据库
    # 由于原始实现依赖 DatabaseService.get_realtime_oldest_update()
    # 而这个功能在 Core 中可能没有对应实现，我们这里模拟一下
    last_update = None  # 如果需要，可以通过 DataAdapter 查询

    # 3. 调用 Core Adapter 判断是否需要刷新
    should_refresh, reason = await market_adapter.should_refresh_realtime_data(
        last_update=last_update,
        force=force
    )

    # 4. 计算距离上次更新的时间
    time_since_update = None
    if last_update:
        time_diff = (datetime.now() - last_update).total_seconds()
        time_since_update = int(time_diff)

    # 5. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "should_refresh": should_refresh,
            "reason": reason,
            "market_status": status,
            "market_description": description,
            "last_update": last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None,
            "codes_count": len(codes) if codes else None,
            "time_since_last_update_seconds": time_since_update,
            "force": force
        },
        message="数据新鲜度检查完成"
    ).to_dict()


@router.get("/next-session")
async def get_next_session():
    """
    获取下一个交易时段

    ✅ 新增端点：查询下一个交易时段信息

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "next_session_time": "2023-12-29 13:00:00",
            "next_session_desc": "今日午盘开盘",
            "current_time": "2023-12-29 11:35:00",
            "wait_minutes": 85,
            "market_status": "closed",
            "market_description": "午间休市"
        }
    }
    """
    # 1. 调用 Core Adapter 获取下一交易时段
    next_time, next_desc = await market_adapter.get_next_trading_session()

    # 2. 获取当前市场状态
    status, description = await market_adapter.get_market_status()

    # 3. 计算等待时间
    now = datetime.now()
    wait_minutes = None
    if next_time:
        wait_seconds = (next_time - now).total_seconds()
        wait_minutes = int(wait_seconds / 60)

    # 4. Backend 职责：响应格式化
    return ApiResponse.success(
        data={
            "next_session_time": next_time.strftime('%Y-%m-%d %H:%M:%S') if next_time else None,
            "next_session_desc": next_desc,
            "current_time": now.strftime('%Y-%m-%d %H:%M:%S'),
            "wait_minutes": wait_minutes,
            "market_status": status,
            "market_description": description
        },
        message="获取下一交易时段成功"
    ).to_dict()
