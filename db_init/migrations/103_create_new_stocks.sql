-- 新股上市列表表（来自 Tushare new_share 接口）
-- 接口：new_share，积分：120
-- 字段：ts_code, sub_code, name, ipo_date, issue_date, amount, market_amount, price, pe, limit_amount, funds, ballot

CREATE TABLE IF NOT EXISTS new_stocks (
    ts_code         VARCHAR(20)     NOT NULL,           -- TS股票代码
    sub_code        VARCHAR(20),                        -- 申购代码
    name            VARCHAR(50)     NOT NULL,           -- 股票名称
    ipo_date        VARCHAR(8),                         -- 上网发行日期 YYYYMMDD
    issue_date      VARCHAR(8),                         -- 上市日期 YYYYMMDD
    amount          NUMERIC(20, 4),                     -- 发行总量（万股）
    market_amount   NUMERIC(20, 4),                     -- 上网发行量（万股）
    price           NUMERIC(10, 4),                     -- 发行价格
    pe              NUMERIC(10, 4),                     -- 发行市盈率
    limit_amount    NUMERIC(20, 4),                     -- 个人申购上限（万股）
    funds           NUMERIC(20, 4),                     -- 募集资金（亿元）
    ballot          NUMERIC(10, 6),                     -- 中签率
    created_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code)
);

CREATE INDEX IF NOT EXISTS idx_new_stocks_ipo_date   ON new_stocks(ipo_date);
CREATE INDEX IF NOT EXISTS idx_new_stocks_issue_date ON new_stocks(issue_date);

COMMENT ON TABLE new_stocks IS 'Tushare new_share 接口 - 新股上市列表';
COMMENT ON COLUMN new_stocks.ipo_date    IS '上网发行日期 YYYYMMDD';
COMMENT ON COLUMN new_stocks.issue_date  IS '上市日期 YYYYMMDD';
COMMENT ON COLUMN new_stocks.amount      IS '发行总量（万股）';
COMMENT ON COLUMN new_stocks.market_amount IS '上网发行量（万股）';
COMMENT ON COLUMN new_stocks.funds       IS '募集资金（亿元）';
COMMENT ON COLUMN new_stocks.ballot      IS '中签率';
