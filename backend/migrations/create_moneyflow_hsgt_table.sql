-- 创建沪深港通资金流向表
CREATE TABLE IF NOT EXISTS moneyflow_hsgt (
    trade_date VARCHAR(8) NOT NULL PRIMARY KEY,  -- 交易日期
    ggt_ss NUMERIC(20, 2),                      -- 港股通（上海）百万元
    ggt_sz NUMERIC(20, 2),                      -- 港股通（深圳）百万元
    hgt NUMERIC(20, 2),                          -- 沪股通（百万元）
    sgt NUMERIC(20, 2),                          -- 深股通（百万元）
    north_money NUMERIC(20, 2),                  -- 北向资金（百万元）
    south_money NUMERIC(20, 2),                  -- 南向资金（百万元）
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_moneyflow_hsgt_trade_date ON moneyflow_hsgt(trade_date DESC);

-- 添加注释
COMMENT ON TABLE moneyflow_hsgt IS '沪深港通资金流向';
COMMENT ON COLUMN moneyflow_hsgt.trade_date IS '交易日期';
COMMENT ON COLUMN moneyflow_hsgt.ggt_ss IS '港股通（上海）百万元';
COMMENT ON COLUMN moneyflow_hsgt.ggt_sz IS '港股通（深圳）百万元';
COMMENT ON COLUMN moneyflow_hsgt.hgt IS '沪股通（百万元）';
COMMENT ON COLUMN moneyflow_hsgt.sgt IS '深股通（百万元）';
COMMENT ON COLUMN moneyflow_hsgt.north_money IS '北向资金（百万元）';
COMMENT ON COLUMN moneyflow_hsgt.south_money IS '南向资金（百万元）';