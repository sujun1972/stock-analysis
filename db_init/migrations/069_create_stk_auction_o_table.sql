-- 股票开盘集合竞价数据表
-- 用于存储股票开盘9:30集合竞价数据
-- 数据来源：Tushare pro.stk_auction_o()
-- 积分消耗：需要开通股票分钟权限
-- 说明：每天盘后更新，单次请求最大返回10000行数据

CREATE TABLE IF NOT EXISTS stk_auction_o (
    ts_code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    close NUMERIC(10, 2),
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    vol NUMERIC(20, 2),
    amount NUMERIC(20, 2),
    vwap NUMERIC(10, 3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_auction_o_trade_date ON stk_auction_o(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_auction_o_ts_code ON stk_auction_o(ts_code);

-- 添加表注释
COMMENT ON TABLE stk_auction_o IS '股票开盘集合竞价数据（Tushare stk_auction_o接口）- 每天盘后更新';
COMMENT ON COLUMN stk_auction_o.ts_code IS '股票代码';
COMMENT ON COLUMN stk_auction_o.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN stk_auction_o.close IS '开盘集合竞价收盘价';
COMMENT ON COLUMN stk_auction_o.open IS '开盘集合竞价开盘价';
COMMENT ON COLUMN stk_auction_o.high IS '开盘集合竞价最高价';
COMMENT ON COLUMN stk_auction_o.low IS '开盘集合竞价最低价';
COMMENT ON COLUMN stk_auction_o.vol IS '开盘集合竞价成交量';
COMMENT ON COLUMN stk_auction_o.amount IS '开盘集合竞价成交额';
COMMENT ON COLUMN stk_auction_o.vwap IS '开盘集合竞价均价';
