-- 创建龙虎榜机构明细表
CREATE TABLE IF NOT EXISTS top_inst (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    exalter VARCHAR(100) NOT NULL,
    side VARCHAR(1) NOT NULL,
    buy FLOAT,
    buy_rate FLOAT,
    sell FLOAT,
    sell_rate FLOAT,
    net_buy FLOAT,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code, exalter, side)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_top_inst_date ON top_inst(trade_date);
CREATE INDEX IF NOT EXISTS idx_top_inst_code ON top_inst(ts_code);
CREATE INDEX IF NOT EXISTS idx_top_inst_net_buy ON top_inst(net_buy);
CREATE INDEX IF NOT EXISTS idx_top_inst_side ON top_inst(side);

-- 添加表注释
COMMENT ON TABLE top_inst IS '龙虎榜机构明细（Tushare top_inst接口）';
COMMENT ON COLUMN top_inst.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN top_inst.ts_code IS '股票代码';
COMMENT ON COLUMN top_inst.exalter IS '营业部名称';
COMMENT ON COLUMN top_inst.side IS '买卖类型（0：买入金额最大的前5名，1：卖出金额最大的前5名）';
COMMENT ON COLUMN top_inst.buy IS '买入额（元）';
COMMENT ON COLUMN top_inst.buy_rate IS '买入占总成交比例（%）';
COMMENT ON COLUMN top_inst.sell IS '卖出额（元）';
COMMENT ON COLUMN top_inst.sell_rate IS '卖出占总成交比例（%）';
COMMENT ON COLUMN top_inst.net_buy IS '净成交额（元）';
COMMENT ON COLUMN top_inst.reason IS '上榜理由';
