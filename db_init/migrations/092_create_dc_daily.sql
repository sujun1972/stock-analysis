-- 092_create_dc_daily.sql
-- 东方财富概念板块行情数据表

CREATE TABLE IF NOT EXISTS dc_daily (
    ts_code VARCHAR(20) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    close NUMERIC(20, 4),
    open NUMERIC(20, 4),
    high NUMERIC(20, 4),
    low NUMERIC(20, 4),
    change NUMERIC(20, 4),
    pct_change NUMERIC(10, 4),
    vol NUMERIC(20, 4),
    amount NUMERIC(20, 4),
    swing NUMERIC(10, 4),
    turnover_rate NUMERIC(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE INDEX IF NOT EXISTS idx_dc_daily_trade_date ON dc_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_dc_daily_ts_code ON dc_daily(ts_code);
COMMENT ON TABLE dc_daily IS 'Tushare dc_daily接口 - 东方财富概念板块行情数据';
