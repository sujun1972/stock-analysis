"""
情绪数据查询端点

包含以下功能：
- 每日情绪数据查询
- 涨停板池查询
- 龙虎榜查询
- 交易日历查询
- 统计分析
- 健康检查
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from datetime import datetime, timedelta

from loguru import logger

from app.services.sentiment_service import MarketSentimentService
from app.core.exceptions import DatabaseError
from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse


router = APIRouter()
sentiment_service = MarketSentimentService()


# ========== 交易日历 ==========

@router.get("/calendar")
async def get_trading_calendar(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份"),
    current_user: User = Depends(get_current_active_user)
):
    """
    查询交易日历

    Args:
        year: 年份（可选）
        month: 月份（可选）

    Returns:
        交易日历列表
    """
    try:
        # 默认查询当年
        if not year:
            year = datetime.now().year

        calendar = await sentiment_service.get_trading_calendar(
            year=year,
            month=month
        )

        return ApiResponse.success(data=calendar)

    except DatabaseError as e:
        logger.error(f"查询交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


