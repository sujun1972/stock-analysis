"""
API路由模块
"""

from fastapi import APIRouter

from .endpoints import (
    auth,
    backtest,
    concepts,
    config,
    data,
    dynamic_strategies,
    experiment,
    features,
    market,
    ml,
    profile,
    scheduler,
    stocks,
    strategies,  # Phase 2: 统一策略 API
    strategy,
    strategy_configs,
    sync,
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
router.include_router(strategy.router, prefix="/strategy", tags=["strategy"])

# Phase 2: 统一策略 API (新架构)
router.include_router(strategies.router, prefix="/strategies", tags=["统一策略系统"])

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

__all__ = ["router"]
