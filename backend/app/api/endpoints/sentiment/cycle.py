"""
情绪周期分析端点

包含以下功能：
- 情绪周期查询
- 周期趋势分析
- 游资分析
- 机构排行
- 周期计算
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional

from loguru import logger

from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse


router = APIRouter()

# 尝试加载情绪周期服务
try:
    from app.services.sentiment_cycle_service import SentimentCycleService
    cycle_service = SentimentCycleService()
    _cycle_service_available = True
except Exception as e:
    logger.warning(f"情绪周期服务不可用: {e}")
    _cycle_service_available = False


# ========== 情绪周期相关 ==========

@router.get("/current")
async def get_current_cycle(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前情绪周期阶段

    Returns:
        当前市场情绪周期数据
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        cycle = cycle_service.get_cycle_stage()

        if 'error' in cycle:
            return ApiResponse.error(message=cycle['error'], code=404)

        return ApiResponse.success(data=cycle)

    except Exception as e:
        logger.error(f"获取当前情绪周期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_cycle_trend(
    days: int = Query(30, ge=7, le=90, description="天数"),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取情绪周期趋势（近N天）

    Returns:
        趋势图数据
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        trend = cycle_service.get_cycle_trend(days=days)

        return ApiResponse.success(data=trend)

    except Exception as e:
        logger.error(f"获取情绪周期趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 游资分析相关 ==========

@router.get("/hot-money/institution-top")
async def get_institution_top_stocks(
    date: Optional[str] = Query(None, description="日期"),
    limit: int = Query(3, ge=1, le=10)
):
    """
    获取机构净买入排行

    Returns:
        机构净买入前N的个股
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_institution_ranking(
            date=date,
            limit=limit
        )

        return ApiResponse.success(data=ranking)

    except Exception as e:
        logger.error(f"获取机构排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-money/top-tier-limit-up")
async def get_top_tier_limit_up_stocks(
    date: Optional[str] = Query(None, description="日期"),
    seat_type: str = Query("top_tier", description="席位类型"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    获取顶级游资主导打板的个股

    Args:
        date: 日期
        seat_type: 席位类型 (top_tier/famous)
        limit: 返回数量

    Returns:
        游资打板排行榜
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_hot_money_ranking(
            date=date,
            seat_type=seat_type,
            limit=limit
        )

        return ApiResponse.success(data=ranking)

    except Exception as e:
        logger.error(f"获取游资打板排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-money/activity-ranking")
async def get_hot_money_activity_ranking(
    days: int = Query(30, ge=7, le=90, description="统计天数"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    获取游资活跃度排行榜

    Returns:
        游资活跃度排行
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_hot_money_activity_ranking(
            days=days,
            limit=limit
        )

        return ApiResponse.success(data=ranking)

    except Exception as e:
        logger.error(f"获取游资活跃度排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 周期计算 ==========

@router.post("/calculate")
async def calculate_cycle(
    date: str = Query(..., description="日期(YYYY-MM-DD)"),
    current_user: User = Depends(require_admin)
):
    """
    手动触发情绪周期计算

    Args:
        date: 日期

    Returns:
        计算结果
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        # 检查是否为交易日，如果不是，自动转换为最近的交易日
        original_date = date
        is_trading = cycle_service.is_trading_day(date)

        if not is_trading:
            # 获取之前最近的交易日
            nearest_date = cycle_service.get_nearest_trading_date(date, direction='before')

            if not nearest_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"{date} 非交易日，且无法找到之前的交易日"
                )

            logger.info(f"{date} 非交易日，自动使用最近交易日 {nearest_date}")
            date = nearest_date

        # 执行计算
        cycle_service.sync_cycle_calculation(date)

        # 返回计算结果
        cycle = cycle_service.get_cycle_stage(date)

        # 如果日期被调整，在消息中说明
        message = "计算成功"
        if original_date != date:
            message = f"{original_date} 非交易日，已计算最近交易日 {date} 的数据"

        return ApiResponse.success(message=message, data=cycle)

    except Exception as e:
        logger.error(f"计算情绪周期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
