-- 创建每日筹码分布表 (cyq_chips)
-- 来源：Tushare cyq_chips 接口
-- 描述：获取A股每日的筹码分布情况，提供各价位占比
-- 积分消耗：5000积分每天20000次，10000积分每天200000次
-- 数据起始：2018年

CREATE TABLE IF NOT EXISTS cyq_chips (
    ts_code VARCHAR(10) NOT NULL,               -- 股票代码
    trade_date VARCHAR(8) NOT NULL,             -- 交易日期 YYYYMMDD
    price NUMERIC(10, 2) NOT NULL,              -- 成本价格
    percent NUMERIC(10, 4),                     -- 价格占比(%)

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 主键：股票代码 + 交易日期 + 价格（唯一组合）
    PRIMARY KEY (ts_code, trade_date, price)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cyq_chips_trade_date ON cyq_chips(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_cyq_chips_ts_code ON cyq_chips(ts_code);
CREATE INDEX IF NOT EXISTS idx_cyq_chips_code_date ON cyq_chips(ts_code, trade_date DESC);

-- 添加表注释
COMMENT ON TABLE cyq_chips IS 'Tushare cyq_chips 接口 - 每日筹码分布数据（2018年起）';
COMMENT ON COLUMN cyq_chips.ts_code IS '股票代码';
COMMENT ON COLUMN cyq_chips.trade_date IS '交易日期，格式：YYYYMMDD';
COMMENT ON COLUMN cyq_chips.price IS '成本价格';
COMMENT ON COLUMN cyq_chips.percent IS '价格占比(%)';
COMMENT ON COLUMN cyq_chips.created_at IS '记录创建时间';
COMMENT ON COLUMN cyq_chips.updated_at IS '记录更新时间';
