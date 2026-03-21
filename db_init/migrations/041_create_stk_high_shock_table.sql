-- 创建个股严重异常波动表
CREATE TABLE IF NOT EXISTS stk_high_shock (
    ts_code VARCHAR(10) NOT NULL,           -- 股票代码
    trade_date VARCHAR(8) NOT NULL,         -- 公告日期 (YYYYMMDD)
    name VARCHAR(50),                       -- 股票名称
    trade_market VARCHAR(20),               -- 交易所
    reason TEXT,                            -- 异常说明
    period VARCHAR(50),                     -- 异常期间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_high_shock_trade_date ON stk_high_shock(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_high_shock_ts_code ON stk_high_shock(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_high_shock_market ON stk_high_shock(trade_market);

-- 添加表注释
COMMENT ON TABLE stk_high_shock IS 'Tushare接口stk_high_shock: 根据证券交易所交易规则的有关规定,交易所每日发布股票交易严重异常波动情况';
COMMENT ON COLUMN stk_high_shock.ts_code IS '股票代码';
COMMENT ON COLUMN stk_high_shock.trade_date IS '公告日期 (YYYYMMDD格式)';
COMMENT ON COLUMN stk_high_shock.name IS '股票名称';
COMMENT ON COLUMN stk_high_shock.trade_market IS '交易所';
COMMENT ON COLUMN stk_high_shock.reason IS '异常说明';
COMMENT ON COLUMN stk_high_shock.period IS '异常期间';
