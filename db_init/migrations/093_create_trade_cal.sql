-- 交易日历表
-- Tushare trade_cal 接口数据
-- 2000积分/次

CREATE TABLE IF NOT EXISTS trade_cal (
    exchange     VARCHAR(10)  NOT NULL,
    cal_date     VARCHAR(8)   NOT NULL,
    is_open      SMALLINT     NOT NULL DEFAULT 0,
    pretrade_date VARCHAR(8)  NULL,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (exchange, cal_date)
);

CREATE INDEX IF NOT EXISTS idx_trade_cal_date    ON trade_cal(cal_date);
CREATE INDEX IF NOT EXISTS idx_trade_cal_is_open ON trade_cal(exchange, is_open);

COMMENT ON TABLE  trade_cal              IS 'Tushare 交易日历（trade_cal 接口）';
COMMENT ON COLUMN trade_cal.exchange     IS '交易所代码（SSE/SZSE/CFFEX/SHFE/CZCE/DCE/INE）';
COMMENT ON COLUMN trade_cal.cal_date     IS '日历日期（YYYYMMDD）';
COMMENT ON COLUMN trade_cal.is_open      IS '是否交易日：0=休市 1=交易';
COMMENT ON COLUMN trade_cal.pretrade_date IS '上一个交易日（YYYYMMDD）';
