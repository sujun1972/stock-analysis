-- 创建AH股比价表
-- Tushare接口: stk_ah_comparison
-- 描述: AH股比价数据，可根据交易日期获取历史数据
-- 权限: 5000积分起
-- 数据起始: 2025-08-12

CREATE TABLE IF NOT EXISTS stk_ah_comparison (
    hk_code VARCHAR(10) NOT NULL,           -- 港股股票代码 (xxxxx.HK)
    ts_code VARCHAR(10) NOT NULL,           -- A股股票代码 (xxxxxx.SH/SZ/BJ)
    trade_date VARCHAR(8) NOT NULL,         -- 交易日期 (YYYYMMDD)
    hk_name VARCHAR(50),                    -- 港股股票名称
    hk_pct_chg DECIMAL(10, 2),              -- 港股股票涨跌幅
    hk_close DECIMAL(10, 2),                -- 港股股票收盘价
    name VARCHAR(50),                       -- A股股票名称
    close DECIMAL(10, 2),                   -- A股股票收盘价
    pct_chg DECIMAL(10, 2),                 -- A股股票涨跌幅
    ah_comparison DECIMAL(10, 2),           -- 比价(A/H)
    ah_premium DECIMAL(10, 2),              -- 溢价(A/H)%
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (hk_code, ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_ah_comparison_trade_date ON stk_ah_comparison(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_ah_comparison_hk_code ON stk_ah_comparison(hk_code);
CREATE INDEX IF NOT EXISTS idx_stk_ah_comparison_ts_code ON stk_ah_comparison(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_ah_comparison_ah_premium ON stk_ah_comparison(ah_premium DESC);

COMMENT ON TABLE stk_ah_comparison IS 'AH股比价数据（Tushare stk_ah_comparison接口）';
COMMENT ON COLUMN stk_ah_comparison.hk_code IS '港股股票代码';
COMMENT ON COLUMN stk_ah_comparison.ts_code IS 'A股股票代码';
COMMENT ON COLUMN stk_ah_comparison.trade_date IS '交易日期';
COMMENT ON COLUMN stk_ah_comparison.hk_name IS '港股股票名称';
COMMENT ON COLUMN stk_ah_comparison.hk_pct_chg IS '港股股票涨跌幅';
COMMENT ON COLUMN stk_ah_comparison.hk_close IS '港股股票收盘价';
COMMENT ON COLUMN stk_ah_comparison.name IS 'A股股票名称';
COMMENT ON COLUMN stk_ah_comparison.close IS 'A股股票收盘价';
COMMENT ON COLUMN stk_ah_comparison.pct_chg IS 'A股股票涨跌幅';
COMMENT ON COLUMN stk_ah_comparison.ah_comparison IS '比价(A/H)';
COMMENT ON COLUMN stk_ah_comparison.ah_premium IS '溢价(A/H)%';
