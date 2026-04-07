-- 创建中央结算系统持股明细表
CREATE TABLE IF NOT EXISTS ccass_hold_detail (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    col_participant_id VARCHAR(100) NOT NULL,
    col_participant_name VARCHAR(200),
    col_shareholding BIGINT,
    col_shareholding_percent DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code, col_participant_id)
);

CREATE INDEX IF NOT EXISTS idx_ccass_hold_detail_trade_date ON ccass_hold_detail(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_ccass_hold_detail_ts_code ON ccass_hold_detail(ts_code);
CREATE INDEX IF NOT EXISTS idx_ccass_hold_detail_participant_id ON ccass_hold_detail(col_participant_id);

COMMENT ON TABLE ccass_hold_detail IS 'Tushare 中央结算系统持股明细（ccass_hold_detail），数据覆盖全历史，8000积分/次';
COMMENT ON COLUMN ccass_hold_detail.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN ccass_hold_detail.ts_code IS '股票代码';
COMMENT ON COLUMN ccass_hold_detail.name IS '股票名称';
COMMENT ON COLUMN ccass_hold_detail.col_participant_id IS '参与者编号';
COMMENT ON COLUMN ccass_hold_detail.col_participant_name IS '机构名称';
COMMENT ON COLUMN ccass_hold_detail.col_shareholding IS '持股量(股)';
COMMENT ON COLUMN ccass_hold_detail.col_shareholding_percent IS '占已发行股份/权证/单位百分比(%)';
