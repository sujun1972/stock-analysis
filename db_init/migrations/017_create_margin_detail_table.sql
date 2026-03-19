-- 融资融券交易明细表
-- 数据来源：Tushare Pro margin_detail 接口
-- 积分消耗：2000分/次（单次最大6000行）
-- 数据说明：获取沪深两市每日融资融券明细

CREATE TABLE IF NOT EXISTS margin_detail (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期 YYYYMMDD
    ts_code VARCHAR(10) NOT NULL,             -- TS股票代码
    name VARCHAR(50),                         -- 股票名称（20190910后有数据）
    rzye DECIMAL(20,2),                       -- 融资余额(元)
    rqye DECIMAL(20,2),                       -- 融券余额(元)
    rzmre DECIMAL(20,2),                      -- 融资买入额(元)
    rqyl DECIMAL(20,2),                       -- 融券余量(股)
    rzche DECIMAL(20,2),                      -- 融资偿还额(元)
    rqchl DECIMAL(20,2),                      -- 融券偿还量(股)
    rqmcl DECIMAL(20,2),                      -- 融券卖出量(股,份,手)
    rzrqye DECIMAL(20,2),                     -- 融资融券余额(元)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_margin_detail_trade_date ON margin_detail(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_margin_detail_ts_code ON margin_detail(ts_code);
CREATE INDEX IF NOT EXISTS idx_margin_detail_rzrqye ON margin_detail(rzrqye DESC);

-- 添加注释
COMMENT ON TABLE margin_detail IS '融资融券交易明细数据（个股级别）';
COMMENT ON COLUMN margin_detail.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN margin_detail.ts_code IS 'TS股票代码';
COMMENT ON COLUMN margin_detail.name IS '股票名称（20190910后有数据）';
COMMENT ON COLUMN margin_detail.rzye IS '融资余额(元) - 本日融资余额=前日融资余额+本日融资买入-本日融资偿还额';
COMMENT ON COLUMN margin_detail.rqye IS '融券余额(元) - 本日融券余额=本日融券余量×本日收盘价';
COMMENT ON COLUMN margin_detail.rzmre IS '融资买入额(元)';
COMMENT ON COLUMN margin_detail.rqyl IS '融券余量(股) - 本日融券余量=前日融券余量+本日融券卖出量-本日融券买入量-本日现券偿还量';
COMMENT ON COLUMN margin_detail.rzche IS '融资偿还额(元)';
COMMENT ON COLUMN margin_detail.rqchl IS '融券偿还量(股)';
COMMENT ON COLUMN margin_detail.rqmcl IS '融券卖出量(股,份,手)';
COMMENT ON COLUMN margin_detail.rzrqye IS '融资融券余额(元) - 本日融资融券余额=本日融资余额+本日融券余额';
