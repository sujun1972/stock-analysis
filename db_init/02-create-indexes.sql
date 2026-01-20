-- 股票基本信息表索引
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks (symbol);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks (industry);
CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks (market);

-- 价格数据表索引
CREATE INDEX IF NOT EXISTS idx_stock_price_time ON stock_prices_raw (time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_price_code_time ON stock_prices_raw (ts_code, time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_price_code ON stock_prices_raw (ts_code);

-- 启用压缩策略（30天前的数据自动压缩）
SELECT add_compression_policy('stock_prices_raw', INTERVAL '30 days', if_not_exists => TRUE);

-- 数据保留策略（可选：保留5年数据）
-- SELECT add_retention_policy('stock_prices_raw', INTERVAL '5 years', if_not_exists => TRUE);