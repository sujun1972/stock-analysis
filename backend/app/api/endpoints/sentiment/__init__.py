"""
市场情绪API端点包

将原有的 sentiment.py (1018行) 拆分为多个模块：
- query.py - 查询类端点（情绪数据、龙虎榜、交易日历、统计分析）
- sync.py - 同步类端点（数据同步、任务管理）
- cycle.py - 情绪周期端点（周期分析、游资排行）
- ai_analysis.py - AI分析端点（生成、查询）
- schemas.py - Pydantic 数据模型

遵循 Backend 架构规范：
- API层只处理HTTP请求/响应
- 业务逻辑在Service层实现
- 使用Pydantic进行参数验证
"""

from fastapi import APIRouter

from . import query, sync, cycle, ai_analysis


# 创建主路由
router = APIRouter()

# 注册子路由
router.include_router(query.router, tags=["sentiment-query"])
router.include_router(sync.router, tags=["sentiment-sync"])
router.include_router(cycle.router, prefix="/cycle", tags=["sentiment-cycle"])
router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["sentiment-ai"])

__all__ = ["router"]
