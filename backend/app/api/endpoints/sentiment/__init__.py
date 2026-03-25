"""
市场情绪API端点包

模块组成：
- query.py - 查询类端点（交易日历查询）
- sync.py - 同步类端点（数据同步、任务管理）
- ai_analysis.py - AI分析端点（生成、查询）

注：已移除的功能（2026-03-25）
- 市场情绪数据管理（market_sentiment_daily表）
- 涨停板池（limit_up_pool表）
- 龙虎榜数据（dragon_tiger_list表）
- 情绪周期分析（sentiment_cycle表）
"""

from fastapi import APIRouter

from . import query, sync, ai_analysis


# 创建主路由
router = APIRouter()

# 注册子路由
router.include_router(query.router, tags=["sentiment-query"])
router.include_router(sync.router, tags=["sentiment-sync"])
router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["sentiment-ai"])

__all__ = ["router"]
