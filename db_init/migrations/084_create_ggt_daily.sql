-- 港股通每日成交统计表
CREATE TABLE IF NOT EXISTS ggt_daily (
    trade_date VARCHAR(8) NOT NULL,
    buy_amount NUMERIC(20, 4),
    buy_volume NUMERIC(20, 4),
    sell_amount NUMERIC(20, 4),
    sell_volume NUMERIC(20, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
);

CREATE INDEX IF NOT EXISTS idx_ggt_daily_trade_date ON ggt_daily(trade_date DESC);

COMMENT ON TABLE ggt_daily IS 'Tushare ggt_daily 港股通每日成交统计，数据从2014年开始';
COMMENT ON COLUMN ggt_daily.trade_date IS '交易日期 (YYYYMMDD)';
COMMENT ON COLUMN ggt_daily.buy_amount IS '买入成交金额（亿元）';
COMMENT ON COLUMN ggt_daily.buy_volume IS '买入成交笔数（万笔）';
COMMENT ON COLUMN ggt_daily.sell_amount IS '卖出成交金额（亿元）';
COMMENT ON COLUMN ggt_daily.sell_volume IS '卖出成交笔数（万笔）';
