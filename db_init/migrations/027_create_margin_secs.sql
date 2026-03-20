-- 创建融资融券标的表（盘前更新）
-- Tushare 接口: margin_secs
-- 描述: 获取沪深京三大交易所融资融券标的（包括ETF），每天盘前更新
-- 积分消耗: 2000积分

CREATE TABLE IF NOT EXISTS margin_secs (
    id SERIAL PRIMARY KEY,
    trade_date VARCHAR(8) NOT NULL,              -- 交易日期（YYYYMMDD）
    ts_code VARCHAR(20) NOT NULL,                -- 标的代码
    name VARCHAR(100),                           -- 标的名称
    exchange VARCHAR(10),                        -- 交易所（SSE上交所 SZSE深交所 BSE北交所）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_margin_secs_trade_date ON margin_secs(trade_date);
CREATE INDEX IF NOT EXISTS idx_margin_secs_ts_code ON margin_secs(ts_code);
CREATE INDEX IF NOT EXISTS idx_margin_secs_exchange ON margin_secs(exchange);
CREATE INDEX IF NOT EXISTS idx_margin_secs_date_exchange ON margin_secs(trade_date, exchange);

-- 添加表注释
COMMENT ON TABLE margin_secs IS '融资融券标的（盘前更新）- Tushare margin_secs接口';
COMMENT ON COLUMN margin_secs.trade_date IS '交易日期（YYYYMMDD格式）';
COMMENT ON COLUMN margin_secs.ts_code IS '标的代码';
COMMENT ON COLUMN margin_secs.name IS '标的名称';
COMMENT ON COLUMN margin_secs.exchange IS '交易所（SSE上交所 SZSE深交所 BSE北交所）';
