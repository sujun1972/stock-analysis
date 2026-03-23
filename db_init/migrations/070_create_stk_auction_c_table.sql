-- 创建股票收盘集合竞价数据表
-- 数据来源: Tushare API - stk_auction_c
-- 描述: 股票收盘15:00集合竞价数据，每天盘后更新
-- 权限要求: 股票分钟权限
-- 限量: 单次最大返回10000行数据

CREATE TABLE IF NOT EXISTS stk_auction_c (
    ts_code VARCHAR(10) NOT NULL,              -- 股票代码
    trade_date VARCHAR(8) NOT NULL,            -- 交易日期(YYYYMMDD)
    close NUMERIC(10, 2),                      -- 收盘集合竞价收盘价
    open NUMERIC(10, 2),                       -- 收盘集合竞价开盘价
    high NUMERIC(10, 2),                       -- 收盘集合竞价最高价
    low NUMERIC(10, 2),                        -- 收盘集合竞价最低价
    vol NUMERIC(20, 2),                        -- 收盘集合竞价成交量
    amount NUMERIC(20, 2),                     -- 收盘集合竞价成交额
    vwap NUMERIC(10, 3),                       -- 收盘集合竞价均价
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_stk_auction_c_trade_date ON stk_auction_c(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_auction_c_ts_code ON stk_auction_c(ts_code);

-- 添加表注释
COMMENT ON TABLE stk_auction_c IS 'Tushare-股票收盘集合竞价数据(每天15:00盘后更新,需要股票分钟权限)';
COMMENT ON COLUMN stk_auction_c.ts_code IS '股票代码';
COMMENT ON COLUMN stk_auction_c.trade_date IS '交易日期(YYYYMMDD格式)';
COMMENT ON COLUMN stk_auction_c.close IS '收盘集合竞价收盘价';
COMMENT ON COLUMN stk_auction_c.open IS '收盘集合竞价开盘价';
COMMENT ON COLUMN stk_auction_c.high IS '收盘集合竞价最高价';
COMMENT ON COLUMN stk_auction_c.low IS '收盘集合竞价最低价';
COMMENT ON COLUMN stk_auction_c.vol IS '收盘集合竞价成交量';
COMMENT ON COLUMN stk_auction_c.amount IS '收盘集合竞价成交额';
COMMENT ON COLUMN stk_auction_c.vwap IS '收盘集合竞价均价';
