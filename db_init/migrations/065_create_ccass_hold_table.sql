-- 中央结算系统持股汇总表
-- 用于存储中央结算系统（CCASS）持股汇总数据
-- 数据来源：Tushare pro.ccass_hold()
-- 积分消耗：120积分（试用），5000积分（正式）

CREATE TABLE IF NOT EXISTS ccass_hold (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    hk_code VARCHAR(10),
    name VARCHAR(100),
    shareholding BIGINT,
    hold_nums INTEGER,
    hold_ratio NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_ccass_hold_trade_date ON ccass_hold(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_ccass_hold_ts_code ON ccass_hold(ts_code);
CREATE INDEX IF NOT EXISTS idx_ccass_hold_hk_code ON ccass_hold(hk_code);

-- 添加表注释
COMMENT ON TABLE ccass_hold IS '中央结算系统持股汇总（Tushare ccass_hold接口）- 覆盖全部历史数据';
COMMENT ON COLUMN ccass_hold.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN ccass_hold.ts_code IS '股票代码（如 605009.SH）';
COMMENT ON COLUMN ccass_hold.hk_code IS '港交所代码（如 95009）';
COMMENT ON COLUMN ccass_hold.name IS '股票名称';
COMMENT ON COLUMN ccass_hold.shareholding IS '于中央结算系统的持股量(股)';
COMMENT ON COLUMN ccass_hold.hold_nums IS '参与者数目（个）';
COMMENT ON COLUMN ccass_hold.hold_ratio IS '占于上交所上市及交易的A股总数的百分比（%）';
