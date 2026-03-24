-- 创建每日涨跌停价格表
-- Tushare接口：stk_limit
-- 说明：获取全市场每日涨跌停价格，包括涨停价格、跌停价格等
-- 更新时间：每个交易日8点40左右更新当日股票涨跌停价格

CREATE TABLE IF NOT EXISTS stk_limit_d (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    pre_close NUMERIC(10, 2),
    up_limit NUMERIC(10, 2),
    down_limit NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_limit_d_trade_date ON stk_limit_d(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_limit_d_ts_code ON stk_limit_d(ts_code);

-- 添加表注释
COMMENT ON TABLE stk_limit_d IS '每日涨跌停价格 - Tushare stk_limit接口，每个交易日8:40更新';
COMMENT ON COLUMN stk_limit_d.trade_date IS '交易日期 (YYYYMMDD)';
COMMENT ON COLUMN stk_limit_d.ts_code IS '股票代码';
COMMENT ON COLUMN stk_limit_d.pre_close IS '昨日收盘价';
COMMENT ON COLUMN stk_limit_d.up_limit IS '涨停价';
COMMENT ON COLUMN stk_limit_d.down_limit IS '跌停价';
