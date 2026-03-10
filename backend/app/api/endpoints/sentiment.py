"""
市场情绪API端点

提供市场情绪数据的查询和同步接口。
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime

from loguru import logger

from app.services.sentiment_service import MarketSentimentService
from app.core.exceptions import DatabaseError, ExternalAPIError


router = APIRouter()
sentiment_service = MarketSentimentService()


# ========== 情绪数据查询 ==========

@router.get("/daily")
async def get_daily_sentiment(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)，默认为今天")
):
    """
    获取指定日期的市场情绪数据

    Returns:
        包含大盘数据、涨停板池、龙虎榜统计的完整情绪报告
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        report = await sentiment_service.get_sentiment_report(date)

        return {
            "code": 200,
            "message": "success",
            "data": report
        }

    except DatabaseError as e:
        logger.error(f"查询每日情绪数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_sentiment_list(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期")
):
    """
    分页查询情绪数据列表（Admin管理界面用）

    Returns:
        分页的情绪数据列表
    """
    try:
        result = await sentiment_service.get_sentiment_list(
            page=page,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "code": 200,
            "message": "success",
            "data": result
        }

    except DatabaseError as e:
        logger.error(f"查询情绪列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 涨停板池 ==========

@router.get("/limit-up")
async def get_limit_up_pool(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)")
):
    """
    获取涨停板池数据

    包含涨停股票列表、炸板数据、连板天梯等。
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        data = await sentiment_service.get_limit_up_detail(date)

        if not data:
            return {
                "code": 404,
                "message": f"{date}没有涨停板数据",
                "data": None
            }

        return {
            "code": 200,
            "message": "success",
            "data": data
        }

    except DatabaseError as e:
        logger.error(f"查询涨停板池失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limit-up/trend")
async def get_limit_up_trend(
    days: int = Query(30, ge=7, le=90, description="天数")
):
    """
    获取涨停板趋势（近N天）

    Returns:
        涨停、炸板、连板天数的时间序列数据
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        stats = await sentiment_service.get_sentiment_statistics(start_date, end_date)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "trend": stats.get("trend", []),
                "summary": stats.get("limit_up_stats", {})
            }
        }

    except DatabaseError as e:
        logger.error(f"查询涨停板趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 龙虎榜 ==========

@router.get("/dragon-tiger")
async def get_dragon_tiger_list(
    date: Optional[str] = Query(None, description="日期"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    has_institution: Optional[bool] = Query(None, description="是否有机构参与"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    查询龙虎榜数据

    支持按日期、股票代码、是否有机构等条件筛选。
    """
    try:
        result = await sentiment_service.get_dragon_tiger_list(
            date=date,
            stock_code=stock_code,
            has_institution=has_institution,
            page=page,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": result
        }

    except DatabaseError as e:
        logger.error(f"查询龙虎榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dragon-tiger/stock/{stock_code}")
async def get_stock_dragon_tiger_history(
    stock_code: str,
    days: int = Query(90, ge=1, le=365, description="查询天数")
):
    """
    查询个股龙虎榜历史

    Args:
        stock_code: 股票代码
        days: 查询天数

    Returns:
        该股票的龙虎榜历史记录
    """
    try:
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        result = await sentiment_service.get_dragon_tiger_list(
            stock_code=stock_code,
            page=1,
            limit=days  # 查询所有记录
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.get("items", [])
        }

    except DatabaseError as e:
        logger.error(f"查询个股龙虎榜历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交易日历 ==========

@router.get("/calendar")
async def get_trading_calendar(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份")
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

        return {
            "code": 200,
            "message": "success",
            "data": calendar
        }

    except DatabaseError as e:
        logger.error(f"查询交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendar/sync")
async def sync_trading_calendar(
    years: List[int] = Query([datetime.now().year], description="年份列表")
):
    """
    同步交易日历

    Args:
        years: 要同步的年份列表

    Returns:
        同步结果
    """
    try:
        total_count = await sentiment_service.sync_trading_calendar_batch(years)

        return {
            "code": 200,
            "message": f"交易日历同步成功，共{total_count}条记录",
            "data": {
                "years": years,
                "total_count": total_count
            }
        }

    except ExternalAPIError as e:
        logger.error(f"同步交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 数据同步 ==========

@router.post("/sync")
async def sync_sentiment_data(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)"),
    background_tasks: BackgroundTasks = None
):
    """
    手动触发情绪数据同步

    Args:
        date: 日期，默认为今天
        background_tasks: 后台任务

    Returns:
        同步结果
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"手动触发情绪数据同步: {date}")

        # 同步执行（Admin手动触发时需要立即看到结果）
        result = await sentiment_service.sync_daily_sentiment(date)

        if result.get("success"):
            return {
                "code": 200,
                "message": "数据同步成功",
                "data": result
            }
        else:
            error_msg = result.get("error", "未知错误")
            return {
                "code": 500,
                "message": f"数据同步失败: {error_msg}",
                "data": result
            }

    except Exception as e:
        logger.error(f"同步情绪数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计分析 ==========

@router.get("/statistics")
async def get_sentiment_statistics(
    start_date: str = Query(..., description="开始日期(YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期(YYYY-MM-DD)")
):
    """
    获取情绪数据统计分析

    用于Admin看板展示，包括：
    - 平均炸板率
    - 涨停/跌停趋势
    - 连板天数分布
    - 龙虎榜活跃度

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计分析数据
    """
    try:
        stats = await sentiment_service.get_sentiment_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "code": 200,
            "message": "success",
            "data": stats
        }

    except DatabaseError as e:
        logger.error(f"统计分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 健康检查 ==========

@router.get("/health")
async def sentiment_health_check():
    """
    情绪数据模块健康检查

    检查：
    - 数据库连接
    - 最新数据日期
    - 数据完整性
    """
    try:
        # 查询最新数据日期
        latest_date_query = """
            SELECT MAX(trade_date) FROM market_sentiment_daily
        """

        conn = sentiment_service._pool_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(latest_date_query)
        latest_date = cursor.fetchone()[0]
        cursor.close()
        sentiment_service._pool_manager.release_connection(conn)

        return {
            "code": 200,
            "message": "healthy",
            "data": {
                "latest_date": latest_date.strftime('%Y-%m-%d') if latest_date else None,
                "database_connected": True
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": "unhealthy",
            "data": {
                "error": str(e),
                "database_connected": False
            }
        }
