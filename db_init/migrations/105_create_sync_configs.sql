-- 同步配置表
-- 管理所有数据表的同步策略（全量/增量/被动），可在管理页面配置
-- 与 task_metadata.py 中的任务元数据互补：
--   task_metadata.py 描述 Celery 任务本身
--   sync_configs 描述"如何同步这张表"的策略配置

CREATE TABLE IF NOT EXISTS sync_configs (
    id SERIAL PRIMARY KEY,
    table_key VARCHAR(100) UNIQUE NOT NULL,      -- 数据表标识（与 data_ops CLEARABLE_TABLES 白名单对应）
    display_name VARCHAR(200) NOT NULL,           -- 页面显示名称（如 "利润表"）
    category VARCHAR(100) NOT NULL,              -- 分类（与 task_metadata 一致）
    display_order INT DEFAULT 999,               -- 同分类内排序

    -- 增量同步配置
    incremental_task_name VARCHAR(200),          -- 增量同步的 Celery 任务名
    incremental_default_days INT DEFAULT 7,      -- 增量同步默认回看天数（可覆盖 default_params.n_days）

    -- 全量同步配置
    full_sync_task_name VARCHAR(200),            -- 全量同步的 Celery 任务名（有则显示全量同步按钮）
    full_sync_strategy VARCHAR(30),              -- 全量策略：'by_ts_code' | 'by_date' | 'by_week' | 'by_month' | 'by_quarter' | 'snapshot' | 'none'
    full_sync_concurrency INT DEFAULT 5,         -- 全量同步并发数（展示用，实际在 Service 层控制）

    -- 被动同步配置
    passive_sync_enabled BOOLEAN DEFAULT FALSE,  -- 是否允许被动同步（访问时检测缺失自动触发）
    passive_sync_task_name VARCHAR(200),         -- 被动触发时调用的 Celery 任务名（通常与增量同步相同）

    -- 元数据
    page_url VARCHAR(300),                       -- 对应前端数据页面的 URL（可点击跳转）
    api_prefix VARCHAR(100),                     -- 后端 API 前缀（如 /income，用于构造 sync-async 端点）
    points_consumption INT,                      -- Tushare 积分消耗（保留字段，页面不展示）
    notes TEXT,                                  -- 备注说明
    api_name VARCHAR(200),                       -- Tushare 接口名称（如 income_vip）
    description TEXT,                            -- 数据说明
    doc_url VARCHAR(500),                        -- Tushare 文档链接
    api_limit INT DEFAULT 2000,                  -- 接口单次请求上限（超出则分页继续，默认 2000）

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sync_configs_category ON sync_configs(category);
CREATE INDEX IF NOT EXISTS idx_sync_configs_order ON sync_configs(category, display_order);

COMMENT ON TABLE sync_configs IS '同步任务配置表 - 管理各数据表的全量/增量/被动同步策略';

-- =============================================
-- 初始数据：覆盖所有已实现的同步任务
-- =============================================

INSERT INTO sync_configs (
    table_key, display_name, category, display_order,
    incremental_task_name, incremental_default_days,
    full_sync_task_name, full_sync_strategy, full_sync_concurrency,
    passive_sync_enabled, passive_sync_task_name,
    page_url, api_prefix, points_consumption, notes
) VALUES

-- ============ 基础数据 ============
('stock_basic',  '股票列表',         '基础数据', 100,
 'sync.stock_list', 1,
 NULL, 'none', 1,
 FALSE, NULL,
 '/data/stock-list', '/stocks/list', NULL, '全量同步即普通同步，同步全状态股票'),

('new_stocks',   'IPO新股列表',      '基础数据', 150,
 'sync.new_stocks', 90,
 NULL, 'none', 1,
 FALSE, NULL,
 '/sync/new-stocks', '/new-stocks', NULL, '增量同步默认回看90天'),

('trade_cal',    '交易日历',         '基础数据', 120,
 'tasks.sync_trade_cal', 365,
 NULL, 'none', 1,
 FALSE, NULL,
 '/data/trade-cal', '/trade-cal', 2000, '全量同步即普通同步'),

('stock_st',     'ST股票列表',       '基础数据', 140,
 'tasks.sync_stock_st', 30,
 NULL, 'none', 1,
 FALSE, NULL,
 '/data/stock-st', '/stock-st', 3000, '特殊：2交易日/批，10并发'),

-- ============ 行情数据 ============
('stock_daily',  '股票日线数据',       '行情数据', 205,
 'tasks.sync_daily_recent_all', 7,
 'tasks.sync_daily_full_history', 'by_ts_code', 8,
 TRUE, 'tasks.sync_daily_single',
 '/market/daily', '/stock-daily', 120, '全量约11分钟，逐只同步'),

('adj_factor',   '复权因子',           '行情数据', 206,
 'tasks.sync_adj_factor', 7,
 'tasks.sync_adj_factor_full_history', 'by_ts_code', 8,
 FALSE, NULL,
 '/market/adj-factor', '/adj-factor', 2000, NULL),

('daily_basic',  '每日指标',           '行情数据', 207,
 'tasks.sync_daily_basic', 7,
 'tasks.sync_daily_basic_full_history', 'by_ts_code', 8,
 FALSE, NULL,
 '/market/daily-basic', '/daily-basic', 2000, NULL),

('stk_limit_d',  '每日涨跌停价格',     '行情数据', 208,
 'tasks.sync_stk_limit_d', 7,
 'tasks.sync_stk_limit_d_full_history', 'by_ts_code', 3,
 FALSE, NULL,
 '/market/stk-limit-d', '/stk-limit-d', 2000, NULL),

('suspend',      '每日停复牌信息',     '行情数据', 209,
 'tasks.sync_suspend', 30,
 'tasks.sync_suspend_full_history', 'by_week', 5,
 FALSE, NULL,
 '/market/suspend', '/suspend', NULL, '按7天窗口切片'),

('hsgt_top10',   '沪深股通十大成交股', '行情数据', 210,
 'tasks.sync_hsgt_top10', 30,
 'tasks.sync_hsgt_top10_full_history', 'by_month', 5,
 FALSE, NULL,
 '/market/hsgt-top10', '/hsgt-top10', NULL, '按月切片'),

('ggt_top10',    '港股通十大成交股',   '行情数据', 211,
 'tasks.sync_ggt_top10', 30,
 'tasks.sync_ggt_top10_full_history', 'by_date', 10,
 FALSE, NULL,
 '/market/ggt-top10', '/ggt-top10', NULL, '逐交易日，10并发'),

('ggt_daily',    '港股通每日成交统计', '行情数据', 212,
 'tasks.sync_ggt_daily', 90,
 'tasks.sync_ggt_daily_full_history', 'by_date', 3,
 FALSE, NULL,
 '/market/ggt-daily', '/ggt-daily', 2000, '按年切片'),

('ggt_monthly',  '港股通每月成交统计', '行情数据', 213,
 'tasks.sync_ggt_monthly', 365,
 NULL, 'none', 1,
 FALSE, NULL,
 '/market/ggt-monthly', '/ggt-monthly', 5000, NULL),

-- ============ 资金流向 ============
('moneyflow',           '个股资金流向（Tushare）', '资金流向', 310,
 'tasks.sync_moneyflow', 7,
 'tasks.sync_moneyflow_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/moneyflow/stock', '/moneyflow', 2000, NULL),

('moneyflow_stock_dc',  '个股资金流向（DC）',      '资金流向', 311,
 'tasks.sync_moneyflow_stock_dc', 7,
 'tasks.sync_moneyflow_stock_dc_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/moneyflow/stock-dc', '/moneyflow-stock-dc', 5000, NULL),

('moneyflow_ind_dc',    '板块资金流向（DC）',      '资金流向', 312,
 'tasks.sync_moneyflow_ind_dc', 7,
 'tasks.sync_moneyflow_ind_dc_full_history', 'by_month', 5,
 FALSE, NULL,
 '/moneyflow/ind-dc', '/moneyflow-ind-dc', 6000, NULL),

('moneyflow_mkt_dc',    '大盘资金流向（DC）',      '资金流向', 313,
 'tasks.sync_moneyflow_mkt_dc', 7,
 'tasks.sync_moneyflow_mkt_dc_full_history', 'by_month', 5,
 FALSE, NULL,
 '/moneyflow/mkt-dc', '/moneyflow-mkt-dc', 120, NULL),

('moneyflow_hsgt',      '沪深港通资金流向',        '资金流向', 314,
 'tasks.sync_moneyflow_hsgt', 30,
 'tasks.sync_moneyflow_hsgt_full_history', 'by_month', 5,
 FALSE, NULL,
 '/moneyflow/hsgt', '/moneyflow-hsgt', 2000, NULL),

-- ============ 两融及转融通 ============
('margin',        '融资融券交易汇总', '两融及转融通', 510,
 'tasks.sync_margin', 30,
 NULL, 'none', 1,
 FALSE, NULL,
 '/margin/summary', '/margin', NULL, NULL),

('margin_detail', '融资融券交易明细', '两融及转融通', 515,
 'tasks.sync_margin_detail', 30,
 NULL, 'none', 1,
 FALSE, NULL,
 '/margin/detail', '/margin-detail', 2000, NULL),

('margin_secs',   '融资融券标的',     '两融及转融通', 520,
 'extended.sync_margin_secs', 1,
 NULL, 'none', 1,
 FALSE, NULL,
 '/margin/secs', '/margin-secs', NULL, '盘前每日更新'),

('slb_len',       '转融资交易汇总',   '两融及转融通', 525,
 'tasks.sync_slb_len', 30,
 NULL, 'none', 1,
 FALSE, NULL,
 '/margin/slb-len', '/slb-len', 2000, NULL),

-- ============ 打板专题 ============
('top_list',   '龙虎榜每日明细',   '打板专题', 550,
 'tasks.sync_top_list', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/top-list', '/top-list', 2000, NULL),

('top_inst',   '龙虎榜机构明细',   '打板专题', 551,
 'tasks.sync_top_inst', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/top-inst', '/top-inst', 5000, NULL),

('limit_list', '涨跌停列表',       '打板专题', 552,
 'tasks.sync_limit_list', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/limit-list', '/limit-list', 5000, NULL),

('limit_step', '连板天梯',         '打板专题', 553,
 'tasks.sync_limit_step', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/limit-step', '/limit-step', 8000, NULL),

('limit_cpt',  '最强板块统计',     '打板专题', 554,
 'tasks.sync_limit_cpt', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/limit-cpt', '/limit-cpt', 8000, NULL),

('dc_index',   '东方财富板块数据', '打板专题', 555,
 'tasks.sync_dc_index', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/dc-index', '/dc-index', 6000, NULL),

('dc_member',  '东方财富板块成分', '打板专题', 556,
 'tasks.sync_dc_member', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/dc-member', '/dc-member', 6000, NULL),

('dc_daily',   '东财概念板块行情', '打板专题', 557,
 'tasks.sync_dc_daily', 7,
 NULL, 'none', 1,
 FALSE, NULL,
 '/boardgame/dc-daily', '/dc-daily', 6000, NULL),

-- ============ 特色数据 ============
('report_rc',        '卖方盈利预测',         '特色数据', 400,
 'tasks.sync_report_rc', 30,
 'tasks.sync_report_rc_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/report-rc', '/report-rc', 8000, NULL),

('cyq_perf',         '每日筹码及胜率',       '特色数据', 401,
 'tasks.sync_cyq_perf', 7,
 'tasks.sync_cyq_perf_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/features/cyq-perf', '/cyq-perf', 5000, NULL),

('cyq_chips',        '每日筹码分布',         '特色数据', 402,
 'tasks.sync_cyq_chips', 7,
 'tasks.sync_cyq_chips_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/features/cyq-chips', '/cyq-chips', 5000, NULL),

('ccass_hold',       '中央结算系统持股汇总', '特色数据', 403,
 'tasks.sync_ccass_hold', 30,
 'tasks.sync_ccass_hold_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/ccass-hold', '/ccass-hold', 5000, NULL),

('ccass_hold_detail','中央结算系统持股明细', '特色数据', 404,
 'tasks.sync_ccass_hold_detail', 30,
 'tasks.sync_ccass_hold_detail_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/ccass-hold-detail', '/ccass-hold-detail', 8000, NULL),

('hk_hold',          '北向资金持股',         '特色数据', 405,
 'tasks.sync_hk_hold', 90,
 'tasks.sync_hk_hold_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/hk-hold', '/hk-hold', 2000, '2024-08改为季度披露'),

('stk_auction_o',    '股票开盘集合竞价',     '特色数据', 406,
 'tasks.sync_stk_auction_o', 30,
 'tasks.sync_stk_auction_o_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/stk-auction-o', '/stk-auction-o', NULL, NULL),

('stk_auction_c',    '股票收盘集合竞价',     '特色数据', 407,
 'tasks.sync_stk_auction_c', 30,
 'tasks.sync_stk_auction_c_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/stk-auction-c', '/stk-auction-c', NULL, NULL),

('stk_nineturn',     '神奇九转指标',         '特色数据', 408,
 'tasks.sync_stk_nineturn', 30,
 'tasks.sync_stk_nineturn_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/stk-nineturn', '/stk-nineturn', 6000, NULL),

('stk_ah_comparison','AH股比价',             '特色数据', 409,
 'tasks.sync_stk_ah_comparison', 30,
 'tasks.sync_stk_ah_comparison_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/stk-ah-comparison', '/stk-ah-comparison', 5000, NULL),

('stk_surv',         '机构调研表',           '特色数据', 410,
 'tasks.sync_stk_surv', 30,
 'tasks.sync_stk_surv_full_history', 'by_month', 5,
 FALSE, NULL,
 '/features/stk-surv', '/stk-surv', 5000, NULL),

('broker_recommend', '券商每月荐股',         '特色数据', 411,
 'tasks.sync_broker_recommend', 90,
 'tasks.sync_broker_recommend_full_history', 'by_month_str', 1,
 FALSE, NULL,
 '/features/broker-recommend', '/broker-recommend', 6000, NULL),

-- ============ 参考数据 ============
('stk_shock',       '个股异常波动',       '参考数据', 450,
 'tasks.sync_stk_shock', 30,
 NULL, 'snapshot', 1,
 FALSE, NULL,
 '/reference-data/stk-shock', '/stk-shock', 6000, '快照接口，不传日期'),

('stk_high_shock',  '个股严重异常波动',   '参考数据', 451,
 'tasks.sync_stk_high_shock', 30,
 NULL, 'snapshot', 1,
 FALSE, NULL,
 '/reference-data/stk-high-shock', '/stk-high-shock', 6000, '快照接口，不传日期'),

('stk_alert',       '交易所重点提示证券', '参考数据', 452,
 'tasks.sync_stk_alert', 30,
 NULL, 'snapshot', 1,
 FALSE, NULL,
 '/reference-data/stk-alert', '/stk-alert', 6000, '快照接口，不传日期'),

('pledge_stat',     '股权质押统计',       '参考数据', 453,
 'tasks.sync_pledge_stat', 90,
 'tasks.sync_pledge_stat_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/reference-data/pledge-stat', '/pledge-stat', 500, '逐只股票请求'),

('repurchase',      '股票回购',           '参考数据', 454,
 'tasks.sync_repurchase', 90,
 'tasks.sync_repurchase_full_history', 'by_month', 5,
 FALSE, NULL,
 '/reference-data/repurchase', '/repurchase', 600, '按月切片'),

('share_float',     '限售股解禁',         '参考数据', 455,
 'tasks.sync_share_float', 90,
 'tasks.sync_share_float_full_history', 'by_month', 5,
 FALSE, NULL,
 '/reference-data/share-float', '/share-float', 120, '按月切片'),

('block_trade',     '大宗交易',           '参考数据', 456,
 'tasks.sync_block_trade', 30,
 'tasks.sync_block_trade_full_history', 'by_month', 5,
 FALSE, NULL,
 '/reference-data/block-trade', '/block-trade', 300, '按月切片，单次上限1000条'),

('stk_holdernumber','股东人数',           '参考数据', 457,
 'tasks.sync_stk_holdernumber', 90,
 'tasks.sync_stk_holdernumber_full_history', 'by_month', 5,
 FALSE, NULL,
 '/reference-data/stk-holdernumber', '/stk-holdernumber', 600, '按月切片'),

('stk_holdertrade', '股东增减持',         '参考数据', 458,
 'tasks.sync_stk_holdertrade', 90,
 'tasks.sync_stk_holdertrade_full_history', 'by_month', 5,
 FALSE, NULL,
 '/reference-data/stk-holdertrade', '/stk-holdertrade', 2000, '按月切片'),

-- ============ 财务数据 ============
('income',          '利润表',         '财务数据', 800,
 'tasks.sync_income', 90,
 'tasks.sync_income_full_history', 'by_ts_code', 5,
 TRUE, 'tasks.sync_income',
 '/financial/income', '/income', 2000, '逐只股票请求，支持被动同步'),

('balancesheet',    '资产负债表',     '财务数据', 801,
 'tasks.sync_balancesheet', 90,
 'tasks.sync_balancesheet_full_history', 'by_ts_code', 5,
 TRUE, 'tasks.sync_balancesheet',
 '/financial/balancesheet', '/balancesheet', 2000, '逐只股票请求，支持被动同步'),

('cashflow',        '现金流量表',     '财务数据', 802,
 'tasks.sync_cashflow', 90,
 'tasks.sync_cashflow_full_history', 'by_ts_code', 5,
 TRUE, 'tasks.sync_cashflow',
 '/financial/cashflow', '/cashflow', 2000, '逐只股票请求，支持被动同步'),

('forecast',        '业绩预告',       '财务数据', 803,
 'tasks.sync_forecast', 90,
 'tasks.sync_forecast_full_history', 'by_quarter', 5,
 FALSE, NULL,
 '/financial/forecast', '/forecast', 2000, '按季度 period 切片'),

('express',         '业绩快报',       '财务数据', 804,
 'tasks.sync_express', 90,
 'tasks.sync_express_full_history', 'by_quarter', 5,
 FALSE, NULL,
 '/financial/express', '/express', 2000, '按季度 period 切片'),

('dividend',        '分红送股',       '财务数据', 805,
 'tasks.sync_dividend', 90,
 'tasks.sync_dividend_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/financial/dividend', '/dividend', 2000, NULL),

('fina_indicator',  '财务指标',       '财务数据', 806,
 'tasks.sync_fina_indicator', 90,
 'tasks.sync_fina_indicator_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/financial/fina-indicator', '/fina-indicator', 2000, NULL),

('fina_audit',      '财务审计意见',   '财务数据', 807,
 'tasks.sync_fina_audit', 90,
 NULL, 'none', 1,
 FALSE, NULL,
 '/financial/fina-audit', '/fina-audit', 500, '必填ts_code，无法全市场拉取'),

('fina_mainbz',     '主营业务构成',   '财务数据', 808,
 'tasks.sync_fina_mainbz', 90,
 'tasks.sync_fina_mainbz_full_history', 'by_ts_code', 5,
 FALSE, NULL,
 '/financial/fina-mainbz', '/fina-mainbz', 2000, NULL),

('disclosure_date', '财报披露计划',   '财务数据', 809,
 'tasks.sync_disclosure_date', 90,
 NULL, 'none', 1,
 FALSE, NULL,
 '/financial/disclosure-date', '/disclosure-date', 500, NULL)

ON CONFLICT (table_key) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    incremental_task_name = EXCLUDED.incremental_task_name,
    incremental_default_days = EXCLUDED.incremental_default_days,
    full_sync_task_name = EXCLUDED.full_sync_task_name,
    full_sync_strategy = EXCLUDED.full_sync_strategy,
    full_sync_concurrency = EXCLUDED.full_sync_concurrency,
    passive_sync_enabled = EXCLUDED.passive_sync_enabled,
    passive_sync_task_name = EXCLUDED.passive_sync_task_name,
    page_url = EXCLUDED.page_url,
    api_prefix = EXCLUDED.api_prefix,
    points_consumption = EXCLUDED.points_consumption,
    notes = EXCLUDED.notes,
    -- api_name/description/doc_url/api_limit 由管理页面手动维护，迁移脚本不覆盖
    updated_at = NOW();
