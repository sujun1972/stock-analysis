-- 沪深港股通持股明细表
-- 用于存储沪深港股通持股明细数据
-- 数据来源：Tushare pro.hk_hold()
-- 积分消耗：120积分（试用），2000积分（正式）
-- 说明：交易所于从2024年8月20开始停止发布日度北向资金数据，改为季度披露

CREATE TABLE IF NOT EXISTS hk_hold (
    code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    vol BIGINT,
    ratio NUMERIC(10, 2),
    exchange VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, trade_date, exchange)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hk_hold_trade_date ON hk_hold(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_hk_hold_ts_code ON hk_hold(ts_code);
CREATE INDEX IF NOT EXISTS idx_hk_hold_exchange ON hk_hold(exchange);
CREATE INDEX IF NOT EXISTS idx_hk_hold_code ON hk_hold(code);

-- 添加表注释
COMMENT ON TABLE hk_hold IS '沪深港股通持股明细（Tushare hk_hold接口）- 交易所从2024年8月20起改为季度披露';
COMMENT ON COLUMN hk_hold.code IS '原始代码（如 90000）';
COMMENT ON COLUMN hk_hold.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN hk_hold.ts_code IS 'TS代码（如 600000.SH）';
COMMENT ON COLUMN hk_hold.name IS '股票名称';
COMMENT ON COLUMN hk_hold.vol IS '持股数量(股)';
COMMENT ON COLUMN hk_hold.ratio IS '持股占比（%），占已发行股份百分比';
COMMENT ON COLUMN hk_hold.exchange IS '类型：SH沪股通（北向）SZ深股通（北向）HK港股通（南向持股）';
