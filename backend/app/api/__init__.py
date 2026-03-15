"""
API路由模块
"""

from fastapi import APIRouter

from .endpoints import (
    admin_strategy_review,
    ai_strategy,
    auth,
    backtest,
    backtest_history,
    concepts,
    config,
    data,
    dynamic_strategies,
    experiment,
    features,
    llm_logs,
    market,
    ml,
    notification_channels,
    notifications,
    premarket,
    profile,
    prompt_templates,
    scheduler,
    sentiment,
    stocks,
    strategies,  # Phase 2: 统一策略 API
    strategy,
    strategy_configs,
    strategy_publish,
    sync,
    system_logs,
    users,
)

# 创建主路由
router = APIRouter()

# 认证和用户管理路由（无需prefix，已在endpoint中定义）
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(profile.router)

# 注册子路由
router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
router.include_router(concepts.router, prefix="/concepts", tags=["概念板块"])
router.include_router(data.router, prefix="/data", tags=["data"])
router.include_router(features.router, prefix="/features", tags=["features"])
router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
router.include_router(backtest_history.router, prefix="/backtest-history", tags=["回测历史"])
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])

# Phase 2: 统一策略 API (新架构)
router.include_router(strategies.router, prefix="/strategies", tags=["统一策略系统"])
router.include_router(strategy_publish.router, prefix="/strategies", tags=["策略发布"])
router.include_router(admin_strategy_review.router, prefix="/admin/strategies", tags=["管理员审核"])

# Core v6.0 路由 (将逐步废弃)
router.include_router(strategy_configs.router, prefix="/strategy-configs", tags=["策略配置 (旧)"])
router.include_router(dynamic_strategies.router, prefix="/dynamic-strategies", tags=["动态策略 (旧)"])
router.include_router(ml.router, prefix="/ml", tags=["机器学习"])

# 数据引擎路由
router.include_router(config.router, prefix="/config", tags=["配置管理"])
router.include_router(sync.router, prefix="/sync", tags=["数据同步"])
router.include_router(scheduler.router, prefix="/scheduler", tags=["定时任务"])
router.include_router(market.router, prefix="/market", tags=["市场状态"])

# 自动化实验路由
router.include_router(experiment.router, prefix="/experiment", tags=["自动化实验"])

# AI策略生成路由
router.include_router(ai_strategy.router, prefix="/ai-strategy", tags=["AI策略生成"])

# 市场情绪路由
router.include_router(sentiment.router, prefix="/sentiment", tags=["市场情绪"])

# 盘前预期管理路由
router.include_router(premarket.router, prefix="/premarket", tags=["盘前预期管理"])

# LLM调用日志路由
router.include_router(llm_logs.router, tags=["LLM调用日志"])

# 提示词模板管理路由
router.include_router(prompt_templates.router, prefix="/prompt-templates", tags=["提示词模板管理"])

# 系统日志路由
router.include_router(system_logs.router, tags=["系统日志"])

# 通知系统路由
router.include_router(notification_channels.router, prefix="/notification-channels", tags=["通知渠道配置（Admin）"])
router.include_router(notifications.router, prefix="/notifications", tags=["用户通知"])

__all__ = ["router"]
