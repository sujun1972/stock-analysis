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
    celery_tasks,  # Celery 任务状态查询
    concepts,
    config,
    data,
    data_quality,  # 数据质量监控
    dynamic_strategies,
    experiment,
    extended_data,  # 扩展数据接口
    features,
    llm_logs,
    margin,  # 融资融券交易汇总
    margin_detail,  # 融资融券交易明细
    margin_secs,  # 融资融券标的（盘前更新）
    slb_len,  # 转融资交易汇总
    market,
    ml,
    moneyflow,  # 个股资金流向（Tushare标准）
    moneyflow_hsgt,  # 沪深港通资金流向
    moneyflow_mkt_dc,  # 大盘资金流向
    moneyflow_ind_dc,  # 板块资金流向
    moneyflow_stock_dc,  # 个股资金流向（东方财富DC）
    notification_channels,
    notification_monitoring,  # Phase 3: 通知监控
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
    top_list,  # 龙虎榜每日明细
    top_inst,  # 龙虎榜机构明细
    limit_list,  # 涨跌停列表
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
router.include_router(extended_data.router, prefix="/extended-data", tags=["扩展数据"])
router.include_router(data_quality.router, prefix="/data-quality", tags=["数据质量"])
router.include_router(moneyflow.router, prefix="/moneyflow", tags=["个股资金流向（Tushare）"])  # 个股资金流向API（Tushare标准）
router.include_router(moneyflow_hsgt.router, prefix="/moneyflow-hsgt", tags=["沪深港通资金流向"])  # 沪深港通资金流向API
router.include_router(moneyflow_mkt_dc.router, prefix="/moneyflow-mkt-dc", tags=["大盘资金流向"])  # 大盘资金流向API
router.include_router(moneyflow_ind_dc.router, prefix="/moneyflow-ind-dc", tags=["板块资金流向"])  # 板块资金流向API
router.include_router(moneyflow_stock_dc.router, prefix="/moneyflow-stock-dc", tags=["个股资金流向（DC）"])  # 个股资金流向API（东方财富DC）
router.include_router(margin.router, prefix="/margin", tags=["融资融券交易汇总"])  # 融资融券交易汇总API
router.include_router(margin_detail.router, prefix="/margin-detail", tags=["融资融券交易明细"])  # 融资融券交易明细API
router.include_router(margin_secs.router, prefix="/margin-secs", tags=["融资融券标的（盘前更新）"])  # 融资融券标的API
router.include_router(slb_len.router, prefix="/slb-len", tags=["转融资交易汇总"])  # 转融资交易汇总API
router.include_router(top_list.router, prefix="/top-list", tags=["龙虎榜每日明细"])  # 龙虎榜每日明细API
router.include_router(top_inst.router, prefix="/top-inst", tags=["龙虎榜机构明细"])  # 龙虎榜机构明细API
router.include_router(limit_list.router, prefix="/limit-list", tags=["涨跌停列表"])  # 涨跌停列表API
router.include_router(scheduler.router, prefix="/scheduler", tags=["定时任务"])
router.include_router(celery_tasks.router, tags=["Celery任务"])  # Celery 任务状态查询
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
router.include_router(notification_monitoring.router, prefix="/notification-monitoring", tags=["通知系统监控（Admin）"])  # Phase 3

__all__ = ["router"]
