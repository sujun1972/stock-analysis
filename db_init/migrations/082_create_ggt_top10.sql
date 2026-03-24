-- 创建港股通十大成交股表
-- 根据Tushare ggt_top10接口

CREATE TABLE IF NOT EXISTS ggt_top10 (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(20) NOT NULL,
    name VARCHAR(100),
    close DECIMAL(10, 2),
    p_change DECIMAL(10, 4),
    rank INTEGER,
    market_type VARCHAR(2) NOT NULL,
    amount DECIMAL(20, 2),
    net_amount DECIMAL(20, 2),
    sh_amount DECIMAL(20, 2),
    sh_net_amount DECIMAL(20, 2),
    sh_buy DECIMAL(20, 2),
    sh_sell DECIMAL(20, 2),
    sz_amount DECIMAL(20, 2),
    sz_net_amount DECIMAL(20, 2),
    sz_buy DECIMAL(20, 2),
    sz_sell DECIMAL(20, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code, market_type)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_ggt_top10_trade_date ON ggt_top10(trade_date);
CREATE INDEX IF NOT EXISTS idx_ggt_top10_ts_code ON ggt_top10(ts_code);
CREATE INDEX IF NOT EXISTS idx_ggt_top10_market_type ON ggt_top10(market_type);
CREATE INDEX IF NOT EXISTS idx_ggt_top10_rank ON ggt_top10(rank);
CREATE INDEX IF NOT EXISTS idx_ggt_top10_net_amount ON ggt_top10(net_amount);

-- 添加表注释
COMMENT ON TABLE ggt_top10 IS 'Tushare接口: ggt_top10 - 港股通十大成交股，包含每日港股通(沪)、港股通(深)前十大成交详细数据，每天18~20点更新';

-- 添加字段注释
COMMENT ON COLUMN ggt_top10.trade_date IS '交易日期';
COMMENT ON COLUMN ggt_top10.ts_code IS '股票代码';
COMMENT ON COLUMN ggt_top10.name IS '股票名称';
COMMENT ON COLUMN ggt_top10.close IS '收盘价';
COMMENT ON COLUMN ggt_top10.p_change IS '涨跌幅(%)';
COMMENT ON COLUMN ggt_top10.rank IS '资金排名';
COMMENT ON COLUMN ggt_top10.market_type IS '市场类型 2:港股通(沪) 4:港股通(深)';
COMMENT ON COLUMN ggt_top10.amount IS '累计成交金额(元)';
COMMENT ON COLUMN ggt_top10.net_amount IS '净买入金额(元)';
COMMENT ON COLUMN ggt_top10.sh_amount IS '沪市成交金额(元)';
COMMENT ON COLUMN ggt_top10.sh_net_amount IS '沪市净买入金额(元)';
COMMENT ON COLUMN ggt_top10.sh_buy IS '沪市买入金额(元)';
COMMENT ON COLUMN ggt_top10.sh_sell IS '沪市卖出金额(元)';
COMMENT ON COLUMN ggt_top10.sz_amount IS '深市成交金额(元)';
COMMENT ON COLUMN ggt_top10.sz_net_amount IS '深市净买入金额(元)';
COMMENT ON COLUMN ggt_top10.sz_buy IS '深市买入金额(元)';
COMMENT ON COLUMN ggt_top10.sz_sell IS '深市卖出金额(元)';
