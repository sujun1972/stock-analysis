-- 创建港股通每月成交统计表
-- Tushare ggt_monthly 接口：港股通每月成交信息
-- 数据从2014年开始
-- 限量：单次最大1000
-- 积分：5000积分/次

CREATE TABLE IF NOT EXISTS ggt_monthly (
    -- 主键字段
    month VARCHAR(6) NOT NULL,              -- 月度，格式YYYYMM

    -- 日均成交数据（单位：亿元、万笔）
    day_buy_amt NUMERIC(20, 4),             -- 当月日均买入成交金额（亿元）
    day_buy_vol NUMERIC(20, 4),             -- 当月日均买入成交笔数（万笔）
    day_sell_amt NUMERIC(20, 4),            -- 当月日均卖出成交金额（亿元）
    day_sell_vol NUMERIC(20, 4),            -- 当月日均卖出成交笔数（万笔）

    -- 月度总计数据（单位：亿元、万笔）
    total_buy_amt NUMERIC(20, 4),           -- 总买入成交金额（亿元）
    total_buy_vol NUMERIC(20, 4),           -- 总买入成交笔数（万笔）
    total_sell_amt NUMERIC(20, 4),          -- 总卖出成交金额（亿元）
    total_sell_vol NUMERIC(20, 4),          -- 总卖出成交笔数（万笔）

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (month)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_ggt_monthly_month ON ggt_monthly(month DESC);

-- 表注释
COMMENT ON TABLE ggt_monthly IS 'Tushare ggt_monthly接口 - 港股通每月成交统计数据（从2014年开始，5000积分/次）';

-- 列注释
COMMENT ON COLUMN ggt_monthly.month IS '月度，格式YYYYMM';
COMMENT ON COLUMN ggt_monthly.day_buy_amt IS '当月日均买入成交金额（亿元）';
COMMENT ON COLUMN ggt_monthly.day_buy_vol IS '当月日均买入成交笔数（万笔）';
COMMENT ON COLUMN ggt_monthly.day_sell_amt IS '当月日均卖出成交金额（亿元）';
COMMENT ON COLUMN ggt_monthly.day_sell_vol IS '当月日均卖出成交笔数（万笔）';
COMMENT ON COLUMN ggt_monthly.total_buy_amt IS '总买入成交金额（亿元）';
COMMENT ON COLUMN ggt_monthly.total_buy_vol IS '总买入成交笔数（万笔）';
COMMENT ON COLUMN ggt_monthly.total_sell_amt IS '总卖出成交金额（亿元）';
COMMENT ON COLUMN ggt_monthly.total_sell_vol IS '总卖出成交笔数（万笔）';
