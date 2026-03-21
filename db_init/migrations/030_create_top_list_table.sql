-- 创建龙虎榜每日明细表
CREATE TABLE IF NOT EXISTS top_list (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    close FLOAT,
    pct_change FLOAT,
    turnover_rate FLOAT,
    amount FLOAT,
    l_sell FLOAT,
    l_buy FLOAT,
    l_amount FLOAT,
    net_amount FLOAT,
    net_rate FLOAT,
    amount_rate FLOAT,
    float_values FLOAT,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_top_list_date ON top_list(trade_date);
CREATE INDEX IF NOT EXISTS idx_top_list_code ON top_list(ts_code);
CREATE INDEX IF NOT EXISTS idx_top_list_net_amount ON top_list(net_amount);

-- 添加表注释
COMMENT ON TABLE top_list IS '龙虎榜每日明细（Tushare top_list接口）';
COMMENT ON COLUMN top_list.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN top_list.ts_code IS '股票代码';
COMMENT ON COLUMN top_list.name IS '股票名称';
COMMENT ON COLUMN top_list.close IS '收盘价';
COMMENT ON COLUMN top_list.pct_change IS '涨跌幅（%）';
COMMENT ON COLUMN top_list.turnover_rate IS '换手率（%）';
COMMENT ON COLUMN top_list.amount IS '总成交额（元）';
COMMENT ON COLUMN top_list.l_sell IS '龙虎榜卖出额（元）';
COMMENT ON COLUMN top_list.l_buy IS '龙虎榜买入额（元）';
COMMENT ON COLUMN top_list.l_amount IS '龙虎榜成交额（元）';
COMMENT ON COLUMN top_list.net_amount IS '龙虎榜净买入额（元）';
COMMENT ON COLUMN top_list.net_rate IS '龙虎榜净买额占比（%）';
COMMENT ON COLUMN top_list.amount_rate IS '龙虎榜成交额占比（%）';
COMMENT ON COLUMN top_list.float_values IS '当日流通市值（元）';
COMMENT ON COLUMN top_list.reason IS '上榜理由';
