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
    daily_basic,  # 每日指标数据
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
    hsgt_top10,  # 沪深股通十大成交股
    ggt_top10,  # 港股通十大成交股
    ggt_daily,  # 港股通每日成交统计
    ggt_monthly,  # 港股通每月成交统计
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
    stock_daily,  # 股票日线数据
    stock_list,  # 股票列表管理
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
    limit_step,  # 连板天梯
    limit_cpt,  # 最强板块统计
    report_rc,  # 卖方盈利预测数据
    cyq_perf,  # 每日筹码及胜率
    cyq_chips,  # 每日筹码分布
    ccass_hold,  # 中央结算系统持股汇总
    ccass_hold_detail,  # 中央结算系统持股明细
    hk_hold,  # 沪深港股通持股明细
    stk_auction_o,  # 股票开盘集合竞价
    stk_auction_c,  # 股票收盘集合竞价
    stk_nineturn,  # 神奇九转指标
    stk_ah_comparison,  # AH股比价
    stk_surv,  # 机构调研表
    broker_recommend,  # 券商每月荐股
    stk_shock,  # 个股异常波动
    stk_alert,  # 交易所重点提示证券
    stk_high_shock,  # 个股严重异常波动
    pledge_stat,  # 股权质押统计
    repurchase,  # 股票回购
    share_float,  # 限售股解禁
    forecast,  # 业绩预告
    stk_holdernumber,  # 股东人数
    block_trade,  # 大宗交易
    stk_holdertrade,  # 股东增减持
    income,  # 利润表数据
    balancesheet,  # 资产负债表数据
    cashflow,  # 现金流量表数据
    express,  # 业绩快报
    dividend,  # 分红送股数据
    fina_indicator,  # 财务指标数据
    fina_audit,  # 财务审计意见数据
    fina_mainbz,  # 主营业务构成数据
    disclosure_date,  # 财报披露计划数据
    suspend,  # 每日停复牌信息
    stk_limit_d,  # 每日涨跌停价格
    adj_factor,  # 复权因子
    new_stocks,  # 新股列表
    stock_realtime,  # 实时行情
    users,
)

# 创建主路由
router = APIRouter()

# 认证和用户管理路由（无需prefix，已在endpoint中定义）
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(profile.router)

# 注册子路由
router.include_router(stock_list.router, prefix="/stocks/list", tags=["股票列表管理"])  # 股票列表管理API
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
router.include_router(hsgt_top10.router, prefix="/hsgt-top10", tags=["沪深股通十大成交股"])  # 沪深股通十大成交股API
router.include_router(ggt_top10.router, prefix="/ggt-top10", tags=["港股通十大成交股"])  # 港股通十大成交股API
router.include_router(ggt_daily.router, prefix="/ggt-daily", tags=["港股通每日成交统计"])  # 港股通每日成交统计API
router.include_router(ggt_monthly.router, prefix="/ggt-monthly", tags=["港股通每月成交统计"])  # 港股通每月成交统计API
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
router.include_router(limit_step.router, prefix="/limit-step", tags=["连板天梯"])  # 连板天梯API
router.include_router(limit_cpt.router, prefix="/limit-cpt", tags=["最强板块统计"])  # 最强板块统计API
router.include_router(report_rc.router, prefix="/report-rc", tags=["卖方盈利预测数据"])  # 卖方盈利预测数据API
router.include_router(cyq_perf.router, prefix="/cyq-perf", tags=["每日筹码及胜率"])  # 每日筹码及胜率API
router.include_router(cyq_chips.router, prefix="/cyq-chips", tags=["每日筹码分布"])  # 每日筹码分布API
router.include_router(ccass_hold.router, prefix="/ccass-hold", tags=["中央结算系统持股汇总"])  # 中央结算系统持股汇总API
router.include_router(ccass_hold_detail.router, prefix="/ccass-hold-detail", tags=["中央结算系统持股明细"])  # 中央结算系统持股明细API
router.include_router(hk_hold.router, prefix="/hk-hold", tags=["沪深港股通持股明细"])  # 沪深港股通持股明细API
router.include_router(stk_auction_o.router, prefix="/stk-auction-o", tags=["股票开盘集合竞价"])  # 股票开盘集合竞价API
router.include_router(stk_auction_c.router, prefix="/stk-auction-c", tags=["股票收盘集合竞价"])  # 股票收盘集合竞价API
router.include_router(stk_nineturn.router, prefix="/stk-nineturn", tags=["神奇九转指标"])  # 神奇九转指标API
router.include_router(stk_ah_comparison.router, prefix="/stk-ah-comparison", tags=["AH股比价"])  # AH股比价API
router.include_router(stk_surv.router, prefix="/stk-surv", tags=["机构调研表"])  # 机构调研表API
router.include_router(broker_recommend.router, prefix="/broker-recommend", tags=["券商每月荐股"])  # 券商每月荐股API
router.include_router(stk_shock.router, prefix="/stk-shock", tags=["个股异常波动"])  # 个股异常波动API
router.include_router(stk_alert.router, prefix="/stk-alert", tags=["交易所重点提示证券"])  # 交易所重点提示证券API
router.include_router(stk_high_shock.router, prefix="/stk-high-shock", tags=["个股严重异常波动"])  # 个股严重异常波动API
router.include_router(pledge_stat.router, prefix="/pledge-stat", tags=["股权质押统计"])  # 股权质押统计API
router.include_router(repurchase.router, prefix="/repurchase", tags=["股票回购"])  # 股票回购API
router.include_router(share_float.router, prefix="/share-float", tags=["限售股解禁"])  # 限售股解禁API
router.include_router(forecast.router, prefix="/forecast", tags=["业绩预告"])  # 业绩预告API
router.include_router(stk_holdernumber.router, prefix="/stk-holdernumber", tags=["股东人数"])  # 股东人数API
router.include_router(block_trade.router, prefix="/block-trade", tags=["大宗交易"])  # 大宗交易API
router.include_router(stk_holdertrade.router, prefix="/stk-holdertrade", tags=["股东增减持"])  # 股东增减持API
router.include_router(income.router, prefix="/income", tags=["利润表数据"])  # 利润表数据API
router.include_router(balancesheet.router, prefix="/balancesheet", tags=["资产负债表数据"])  # 资产负债表数据API
router.include_router(cashflow.router, prefix="/cashflow", tags=["现金流量表数据"])  # 现金流量表数据API
router.include_router(express.router, prefix="/express", tags=["业绩快报"])  # 业绩快报API
router.include_router(dividend.router, prefix="/dividend", tags=["分红送股数据"])  # 分红送股数据API
router.include_router(fina_indicator.router, prefix="/fina-indicator", tags=["财务指标数据"])  # 财务指标数据API
router.include_router(fina_audit.router, prefix="/fina-audit", tags=["财务审计意见数据"])  # 财务审计意见数据API
router.include_router(fina_mainbz.router, prefix="/fina-mainbz", tags=["主营业务构成数据"])  # 主营业务构成数据API
router.include_router(disclosure_date.router, prefix="/disclosure-date", tags=["财报披露计划数据"])  # 财报披露计划数据API
router.include_router(suspend.router, prefix="/suspend", tags=["每日停复牌信息"])  # 每日停复牌信息API
router.include_router(stk_limit_d.router, prefix="/stk-limit-d", tags=["每日涨跌停价格"])  # 每日涨跌停价格API
router.include_router(adj_factor.router, prefix="/adj-factor", tags=["复权因子"])  # 复权因子API
router.include_router(daily_basic.router, prefix="/daily-basic", tags=["每日指标数据"])  # 每日指标数据API
router.include_router(new_stocks.router, prefix="/new-stocks", tags=["新股列表"])  # 新股列表API
router.include_router(stock_realtime.router, prefix="/stock-realtime", tags=["实时行情"])  # 实时行情API
router.include_router(stock_daily.router, prefix="/stock-daily", tags=["股票日线数据"])  # 股票日线数据API
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
