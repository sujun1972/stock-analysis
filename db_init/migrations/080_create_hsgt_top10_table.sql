-- 创建沪深股通十大成交股表
CREATE TABLE IF NOT EXISTS hsgt_top10 (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    close DECIMAL(10, 2),
    "change" DECIMAL(10, 2),
    rank INT,
    market_type VARCHAR(1),
    amount DECIMAL(20, 2),
    net_amount DECIMAL(20, 2),
    buy DECIMAL(20, 2),
    sell DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code, market_type)
);

-- 创建索引
CREATE INDEX idx_hsgt_top10_trade_date ON hsgt_top10(trade_date DESC);
CREATE INDEX idx_hsgt_top10_ts_code ON hsgt_top10(ts_code);
CREATE INDEX idx_hsgt_top10_market_type ON hsgt_top10(market_type);
CREATE INDEX idx_hsgt_top10_rank ON hsgt_top10(rank);

-- 添加表和字段注释
COMMENT ON TABLE hsgt_top10 IS 'Tushare接口: hsgt_top10 - 沪深股通十大成交股，包含每日沪股通、深股通前十大成交详细数据';
COMMENT ON COLUMN hsgt_top10.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN hsgt_top10.ts_code IS '股票代码';
COMMENT ON COLUMN hsgt_top10.name IS '股票名称';
COMMENT ON COLUMN hsgt_top10.close IS '收盘价';
COMMENT ON COLUMN hsgt_top10."change" IS '涨跌额';
COMMENT ON COLUMN hsgt_top10.rank IS '资金排名';
COMMENT ON COLUMN hsgt_top10.market_type IS '市场类型 1:沪市 3:深市';
COMMENT ON COLUMN hsgt_top10.amount IS '成交金额(元)';
COMMENT ON COLUMN hsgt_top10.net_amount IS '净成交金额(元)';
COMMENT ON COLUMN hsgt_top10.buy IS '买入金额(元)';
COMMENT ON COLUMN hsgt_top10.sell IS '卖出金额(元)';
