-- 东方财富概念/行业/地域板块数据
CREATE TABLE IF NOT EXISTS dc_index (
    ts_code VARCHAR(20) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    name VARCHAR(100),
    leading_stock VARCHAR(50),
    leading_code VARCHAR(20),
    pct_change FLOAT,
    leading_pct FLOAT,
    total_mv FLOAT,
    turnover_rate FLOAT,
    up_num INTEGER,
    down_num INTEGER,
    idx_type VARCHAR(20),
    level VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE INDEX IF NOT EXISTS idx_dc_index_trade_date ON dc_index(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_dc_index_ts_code ON dc_index(ts_code);
CREATE INDEX IF NOT EXISTS idx_dc_index_idx_type ON dc_index(idx_type);

COMMENT ON TABLE dc_index IS '东方财富板块数据（概念/行业/地域），Tushare dc_index接口，6000积分/次，单次最大5000条';
