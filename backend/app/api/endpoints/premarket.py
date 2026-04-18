"""
盘前预期管理API端点

提供以下功能:
- 盘前数据同步(外盘+新闻)
- AI碰撞分析生成
- 查询分析结果
- 查询外盘数据
- 查询盘前新闻

作者: AI Strategy Team
创建日期: 2026-03-11
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta
from loguru import logger
from typing import Optional
import os

from app.api.error_handler import handle_api_errors
from src.premarket.fetcher import PremarketDataFetcher
from src.database.connection_pool_manager import ConnectionPoolManager
from app.services.premarket_analysis_service import premarket_analysis_service
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.api_response import ApiResponse

# 创建路由（注意：不要在这里加prefix，在__init__.py中统一添加）
router = APIRouter(
    tags=["盘前预期管理"]
)


def get_pool_manager():
    """获取数据库连接池（依赖注入）"""
    db_config = {
        'host': os.getenv('DATABASE_HOST', 'timescaledb'),
        'port': int(os.getenv('DATABASE_PORT', '5432')),
        'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
        'user': os.getenv('DATABASE_USER', 'stock_user'),
        'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
    }
    return ConnectionPoolManager(db_config)


@router.post("/sync")
@handle_api_errors
async def sync_premarket_data(
    date: Optional[str] = Query(None, description="交易日期(YYYY-MM-DD)，默认今天"),
    current_user: User = Depends(get_current_user)
):
    """
    同步盘前数据（外盘 + 新闻）

    **操作**: 抓取隔夜外盘数据和盘前核心新闻

    **流程**:
    1. 判断是否为交易日
    2. 抓取A50期指、中概股、大宗商品、汇率、美股
    3. 抓取财联社/金十快讯（22:00-8:00）
    4. 关键词过滤（超预期、停牌、战争等）

    **返回**: 同步结果和数据统计
    """
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"用户 {current_user.username} 请求同步 {date} 的盘前数据")

    pool_manager = get_pool_manager()
    fetcher = PremarketDataFetcher(pool_manager)

    result = fetcher.sync_premarket_data(date)

    if result.success:
        return ApiResponse.success(
            data={
                "trade_date": result.trade_date,
                "is_trading_day": result.is_trading_day,
                "synced_tables": result.synced_tables,
                "details": result.details
            },
            message="盘前数据同步成功" if result.is_trading_day else f"{date}非交易日，已跳过"
        ).to_dict()
    else:
        return ApiResponse.error(
            message=result.error or "同步失败",
            code=400
        ).to_dict()


@router.post("/collision-analysis/generate")
@handle_api_errors
async def generate_collision_analysis(
    date: Optional[str] = Query(None, description="交易日期(YYYY-MM-DD)，默认今天"),
    provider: str = Query("deepseek", description="AI提供商"),
    model: Optional[str] = Query(None, description="模型名称"),
    current_user: User = Depends(get_current_user)
):
    """
    生成盘前碰撞分析

    **操作**: 调用LLM进行昨晚计划与今晨现实的碰撞测试

    **输入数据**:
    - 输入A: 昨晚的《明日战术日报》
    - 输入B: 今晨的隔夜外盘数据
    - 输入C: 今晨的核心突发新闻

    **输出结果**:
    - 宏观定调（高开/低开预判）
    - 持仓排雷（风险股票提示）
    - 计划修正（取消买入/提前止损）
    - 竞价盯盘（9:15-9:25核心标的）
    - 极简行动指令（200字精华）

    **返回**: 完整的碰撞分析结果
    """
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    logger.info(f"用户 {current_user.username} 请求生成 {date} 的碰撞分析（provider={provider}）")

    result = await premarket_analysis_service.generate_collision_analysis(
        trade_date=date,
        provider=provider,
        model=model
    )

    if result.get("success"):
        return ApiResponse.success(
            data=result,
            message="碰撞分析生成成功"
        ).to_dict()
    else:
        return ApiResponse.error(
            message=result.get("error", "生成失败"),
            code=400
        ).to_dict()


@router.get("/collision-analysis/{date}")
@handle_api_errors
async def get_collision_analysis(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """
    查询指定日期的碰撞分析结果

    **参数**: date - 交易日期(YYYY-MM-DD)

    **返回**: 完整的碰撞分析数据，包括：
    - macro_tone: 宏观定调
    - holdings_alert: 持仓排雷
    - plan_adjustment: 计划修正
    - auction_focus: 竞价盯盘
    - action_command: 行动指令
    - AI元信息（provider、tokens、耗时）
    """
    result = premarket_analysis_service.get_collision_analysis(date)

    if result:
        return ApiResponse.success(
            data=result,
            message="查询成功"
        ).to_dict()
    else:
        raise HTTPException(status_code=404, detail=f"{date} 无碰撞分析数据")


@router.get("/overnight-data/{date}")
@handle_api_errors
async def get_overnight_data(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """
    查询指定日期的隔夜外盘数据

    **参数**: date - 交易日期(YYYY-MM-DD)

    **返回**: 外盘核心指标，包括：
    - A50期指（影响大盘开盘）
    - 中概股指数（外资态度）
    - WTI原油、COMEX黄金、伦敦铜（大宗商品）
    - 美元兑人民币（资金流向）
    - 美股三大指数（参考）
    """
    pool_manager = get_pool_manager()
    conn = pool_manager.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            trade_date, a50_close, a50_change,
            china_concept_close, china_concept_change,
            wti_crude_close, wti_crude_change,
            comex_gold_close, comex_gold_change,
            lme_copper_close, lme_copper_change,
            usdcnh_close, usdcnh_change,
            sp500_close, sp500_change,
            nasdaq_close, nasdaq_change,
            dow_close, dow_change,
            fetch_time
        FROM overnight_market_data
        WHERE trade_date = %s
    """, (date,))

    row = cursor.fetchone()
    cursor.close()
    pool_manager.release_connection(conn)

    if row:
        return ApiResponse.success(
            data={
                "trade_date": str(row[0]),
                "a50": {
                    "close": float(row[1]) if row[1] else 0,
                    "change": float(row[2]) if row[2] else 0
                },
                "china_concept": {
                    "close": float(row[3]) if row[3] else 0,
                    "change": float(row[4]) if row[4] else 0
                },
                "wti_crude": {
                    "close": float(row[5]) if row[5] else 0,
                    "change": float(row[6]) if row[6] else 0
                },
                "comex_gold": {
                    "close": float(row[7]) if row[7] else 0,
                    "change": float(row[8]) if row[8] else 0
                },
                "lme_copper": {
                    "close": float(row[9]) if row[9] else 0,
                    "change": float(row[10]) if row[10] else 0
                },
                "usdcnh": {
                    "close": float(row[11]) if row[11] else 0,
                    "change": float(row[12]) if row[12] else 0
                },
                "sp500": {
                    "close": float(row[13]) if row[13] else 0,
                    "change": float(row[14]) if row[14] else 0
                },
                "nasdaq": {
                    "close": float(row[15]) if row[15] else 0,
                    "change": float(row[16]) if row[16] else 0
                },
                "dow": {
                    "close": float(row[17]) if row[17] else 0,
                    "change": float(row[18]) if row[18] else 0
                },
                "fetch_time": str(row[19]) if row[19] else None
            },
            message="查询成功"
        ).to_dict()
    else:
        raise HTTPException(status_code=404, detail=f"{date} 无外盘数据")


@router.get("/news/{date}")
@handle_api_errors
async def get_premarket_news(
    date: str,
    importance: Optional[str] = Query(None, description="重要性级别过滤: critical/high/medium"),
    current_user: User = Depends(get_current_user)
):
    """
    查询指定日期的盘前核心新闻

    **参数**:
    - date - 交易日期(YYYY-MM-DD)
    - importance - 重要性级别(可选)
      - critical: 核弹级（战争、熔断、崩盘等）
      - high: 高（超预期、停牌、立案调查等）
      - medium: 中（其他关键词）

    **返回**: 新闻列表（最多50条）
    """
    pool_manager = get_pool_manager()
    conn = pool_manager.get_connection()
    cursor = conn.cursor()

    sql = """
        SELECT
            id, trade_date, news_time, source, title,
            content, keywords, importance_level, created_at
        FROM premarket_news_flash
        WHERE trade_date = %s
    """

    params = [date]

    if importance:
        sql += " AND importance_level = %s"
        params.append(importance)

    sql += " ORDER BY news_time DESC LIMIT 50"

    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cursor.close()
    pool_manager.release_connection(conn)

    news_list = []
    for row in rows:
        news_list.append({
            "id": row[0],
            "trade_date": str(row[1]),
            "news_time": str(row[2]),
            "source": row[3],
            "title": row[4],
            "content": row[5],
            "keywords": row[6],
            "importance_level": row[7],
            "created_at": str(row[8]) if row[8] else None
        })

    return ApiResponse.success(
        data={
            "count": len(news_list),
            "news": news_list
        },
        message="查询成功"
    ).to_dict()


@router.get("/history")
@handle_api_errors
async def get_analysis_history(
    limit: int = Query(10, description="返回记录数", ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    查询碰撞分析历史记录

    **参数**: limit - 返回记录数(1-100)

    **返回**: 历史碰撞分析记录列表，包括：
    - 交易日期
    - 行动指令
    - 状态（success/failed）
    - AI模型信息
    - Token消耗
    - 生成耗时

    **用途**: 用于回溯历史建议，评估准确性
    """
    pool_manager = get_pool_manager()
    conn = pool_manager.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            trade_date, action_command, status,
            ai_provider, ai_model, tokens_used,
            generation_time, created_at
        FROM premarket_collision_analysis
        ORDER BY trade_date DESC
        LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()
    cursor.close()
    pool_manager.release_connection(conn)

    history = []
    for row in rows:
        history.append({
            "trade_date": str(row[0]),
            "action_command": row[1],
            "status": row[2],
            "ai_provider": row[3],
            "ai_model": row[4],
            "tokens_used": row[5],
            "generation_time": float(row[6]) if row[6] else 0,
            "created_at": str(row[7]) if row[7] else None
        })

    return ApiResponse.success(
        data=history,
        message="查询成功"
    ).to_dict()
