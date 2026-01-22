"""
市场状态 API
提供交易时段判断、实时数据新鲜度检查等功能
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

from src.utils.market_utils import MarketUtils
from app.services.database_service import DatabaseService

router = APIRouter()


class MarketStatusResponse(BaseModel):
    """市场状态响应"""
    status: str
    description: str
    is_trading: bool
    should_refresh: bool
    next_session_time: Optional[str] = None
    next_session_desc: Optional[str] = None


class DataFreshnessRequest(BaseModel):
    """数据新鲜度检查请求"""
    codes: Optional[list[str]] = None
    force: bool = False


@router.get("/status")
async def get_market_status():
    """
    获取当前市场状态

    Returns:
        市场状态信息，包括是否交易时段、是否需要刷新数据等
    """
    try:
        status, description = MarketUtils.get_market_status()
        is_trading = status in ['trading', 'call_auction']

        # 获取下一个交易时段
        next_time, next_desc = MarketUtils.get_next_trading_session()

        return {
            "code": 200,
            "message": "success",
            "data": {
                "status": status,
                "description": description,
                "is_trading": is_trading,
                "should_refresh": is_trading,
                "next_session_time": next_time.strftime('%Y-%m-%d %H:%M:%S') if next_time else None,
                "next_session_desc": next_desc
            }
        }
    except Exception as e:
        logger.error(f"获取市场状态失败: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.post("/check-freshness")
async def check_data_freshness(request: DataFreshnessRequest):
    """
    检查实时数据的新鲜度

    Args:
        request: 包含股票代码列表和是否强制刷新的标志

    Returns:
        是否需要刷新数据以及原因
    """
    try:
        db_service = DatabaseService()

        # 获取市场状态
        market_status, status_desc = MarketUtils.get_market_status()

        # 如果指定了具体股票，检查这些股票的最后更新时间
        if request.codes and len(request.codes) > 0:
            # 查询指定股票的最后更新时间
            oldest_update = await db_service.get_realtime_oldest_update(request.codes)
        else:
            # 查询所有股票中最旧的更新时间
            oldest_update = await db_service.get_realtime_oldest_update()

        # 判断是否应该刷新
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(
            last_update=oldest_update,
            force=request.force
        )

        return {
            "code": 200,
            "message": "success",
            "data": {
                "should_refresh": should_refresh,
                "reason": reason,
                "market_status": market_status,
                "market_description": status_desc,
                "last_update": oldest_update.strftime('%Y-%m-%d %H:%M:%S') if oldest_update else None,
                "codes_count": len(request.codes) if request.codes else None
            }
        }
    except Exception as e:
        logger.error(f"检查数据新鲜度失败: {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }


@router.get("/realtime-info/{code}")
async def get_realtime_info(code: str):
    """
    获取单只股票的实时数据信息（包括数据新鲜度）

    Args:
        code: 股票代码

    Returns:
        股票实时数据及新鲜度信息
    """
    try:
        db_service = DatabaseService()

        # 获取实时数据
        realtime_data = await db_service.get_stock_realtime(code)

        if not realtime_data:
            return {
                "code": 404,
                "message": "未找到该股票的实时数据",
                "data": None
            }

        # 检查数据新鲜度
        last_update = realtime_data.get('updated_at')
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        market_status, status_desc = MarketUtils.get_market_status()

        return {
            "code": 200,
            "message": "success",
            "data": {
                **realtime_data,
                "should_refresh": should_refresh,
                "refresh_reason": reason,
                "market_status": market_status,
                "market_description": status_desc
            }
        }
    except Exception as e:
        logger.error(f"获取股票实时信息失败 ({code}): {e}")
        return {
            "code": 500,
            "message": str(e),
            "data": None
        }
