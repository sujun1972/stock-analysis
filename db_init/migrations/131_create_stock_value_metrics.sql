-- 股票价值度量快照表（维度型，每股票一行）
-- 计算公式：
--   ROC = EBIT / (净营运资本 + 净固定资产)
--     净营运资本 = total_cur_assets - total_cur_liab
--     净固定资产 = fix_assets（Tushare 口径已扣累计折旧，即 PP&E net；
--                 Greenblatt 原书 Net Fixed Assets 就是 PP&E net，不再扣在建工程）
--   Earnings Yield = EBIT / EV
--     EV = total_mv*10000 + lt_borr + st_borr + bond_payable - money_cap
--   Intrinsic Value = basic_eps * (8.5 + 2g)
--     g 优先取 report_rc 券商一致预期的隐含增长率（研报路径），否则取近 3 年 EPS 历史 CAGR
--     业界通行惯例：g 封顶 15%（研报或历史），防止新股/高成长股算出爆炸 IV
--     g 为负或原料缺失 → intrinsic_value 置 NULL（不显示不可靠数字）

BEGIN;

CREATE TABLE IF NOT EXISTS stock_value_metrics (
    ts_code              VARCHAR(10) PRIMARY KEY,

    -- 魔法公式两指标（《股市稳赚》）
    roc                  NUMERIC(12, 6),           -- 资本收益率（小数，0.25 表示 25%）
    earnings_yield       NUMERIC(12, 6),           -- 收益率（小数，EBIT/EV）

    -- 格雷厄姆内在价值（《聪明的投资者》）
    intrinsic_value      NUMERIC(14, 4),           -- 内在价值（元/股）
    intrinsic_margin     NUMERIC(12, 6),           -- 安全边际 = intrinsic_value/当前价 - 1
    g_rate               NUMERIC(8, 4),            -- 用于 IV 的年化增长率（小数，封顶 0.15）
    g_source             VARCHAR(16),              -- 'analyst' | 'history' | 'na'

    -- 计算原料快照（便于前端 tooltip 展示与审计）
    ebit                 NUMERIC(20, 4),           -- 息税前利润（元）
    basic_eps            NUMERIC(10, 4),           -- 基本每股收益（元）
    total_mv             NUMERIC(20, 4),           -- 总市值（万元，取自 daily_basic）
    ev                   NUMERIC(20, 4),           -- 企业价值（元）
    working_capital      NUMERIC(20, 4),           -- 净营运资本（元）
    net_fixed_assets     NUMERIC(20, 4),           -- 净固定资产（元）
    latest_price         NUMERIC(12, 4),           -- IV 计算使用的价格（来自 daily_basic.close）

    -- 数据期次（审计）
    income_end_date      VARCHAR(8),               -- 使用的 income 报告期（YYYYMMDD）
    balance_end_date     VARCHAR(8),               -- 使用的 balancesheet 报告期（YYYYMMDD）
    quote_trade_date     VARCHAR(8),               -- daily_basic 交易日（YYYYMMDD）

    -- 刷新时间
    computed_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 排序索引：列表页支持 ORDER BY roc DESC / earnings_yield DESC / intrinsic_margin DESC
CREATE INDEX IF NOT EXISTS idx_svm_roc               ON stock_value_metrics(roc DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_svm_earnings_yield    ON stock_value_metrics(earnings_yield DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_svm_intrinsic_margin  ON stock_value_metrics(intrinsic_margin DESC NULLS LAST);

COMMENT ON TABLE  stock_value_metrics IS '股票价值度量快照：魔法公式(ROC/EY) + 格雷厄姆内在价值，维度型，每股票一行最新值';
COMMENT ON COLUMN stock_value_metrics.roc IS '资本收益率 = EBIT / (净营运资本 + 净固定资产)';
COMMENT ON COLUMN stock_value_metrics.earnings_yield IS '收益率 = EBIT / EV（企业价值）';
COMMENT ON COLUMN stock_value_metrics.intrinsic_value IS '格雷厄姆内在价值 = EPS × (8.5 + 2g)';
COMMENT ON COLUMN stock_value_metrics.intrinsic_margin IS '安全边际 = 内在价值/当前价 - 1';
COMMENT ON COLUMN stock_value_metrics.g_rate IS '用于 IV 的年化增长率（封顶 15%）';
COMMENT ON COLUMN stock_value_metrics.g_source IS 'g 来源：analyst=券商研报 / history=历史 CAGR / na=不可用';

COMMIT;
