-- 融资融券交易汇总表
-- 数据来源：Tushare Pro margin 接口
-- 积分消耗：2000分/次
-- 数据说明：从证券交易所网站直接获取，提供有记录以来的全部汇总数据

CREATE TABLE IF NOT EXISTS margin (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期 YYYYMMDD
    exchange_id VARCHAR(10) NOT NULL,         -- 交易所代码（SSE上交所/SZSE深交所/BSE北交所）
    rzye DECIMAL(20,2),                       -- 融资余额(元)
    rzmre DECIMAL(20,2),                      -- 融资买入额(元)
    rzche DECIMAL(20,2),                      -- 融资偿还额(元)
    rqye DECIMAL(20,2),                       -- 融券余额(元)
    rqmcl DECIMAL(20,2),                      -- 融券卖出量(股,份,手)
    rzrqye DECIMAL(20,2),                     -- 融资融券余额(元)
    rqyl DECIMAL(20,2),                       -- 融券余量(股,份,手)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, exchange_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_margin_trade_date ON margin(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_margin_exchange_id ON margin(exchange_id);

-- 添加注释
COMMENT ON TABLE margin IS '融资融券交易汇总数据（按交易所统计）';
COMMENT ON COLUMN margin.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN margin.exchange_id IS '交易所代码（SSE上交所/SZSE深交所/BSE北交所）';
COMMENT ON COLUMN margin.rzye IS '融资余额(元) - 本日融资余额=前日融资余额+本日融资买入-本日融资偿还额';
COMMENT ON COLUMN margin.rzmre IS '融资买入额(元)';
COMMENT ON COLUMN margin.rzche IS '融资偿还额(元)';
COMMENT ON COLUMN margin.rqye IS '融券余额(元) - 本日融券余额=本日融券余量×本日收盘价';
COMMENT ON COLUMN margin.rqmcl IS '融券卖出量(股,份,手)';
COMMENT ON COLUMN margin.rzrqye IS '融资融券余额(元) - 本日融资融券余额=本日融资余额+本日融券余额';
COMMENT ON COLUMN margin.rqyl IS '融券余量(股,份,手) - 本日融券余量=前日融券余量+本日融券卖出量-本日融券买入量-本日现券偿还量';
