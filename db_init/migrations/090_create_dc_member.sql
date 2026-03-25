-- 东方财富板块成分表
-- Tushare接口: dc_member
-- 描述: 获取东方财富板块每日成分数据，可以根据概念板块代码和交易日期，获取历史成分
-- 限量: 单次最大获取5000条数据，可以通过日期和代码循环获取
-- 积分: 6000积分/次

CREATE TABLE IF NOT EXISTS dc_member (
    -- 主键字段
    trade_date VARCHAR(8) NOT NULL,    -- 交易日期（YYYYMMDD格式）
    ts_code VARCHAR(20) NOT NULL,      -- 概念板块代码（如 BK1184.DC）
    con_code VARCHAR(20) NOT NULL,     -- 成分股票代码（如 002117.SZ）

    -- 数据字段
    name VARCHAR(100),                 -- 成分股名称

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 主键和索引
    PRIMARY KEY (trade_date, ts_code, con_code)
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_dc_member_trade_date ON dc_member(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_dc_member_ts_code ON dc_member(ts_code);
CREATE INDEX IF NOT EXISTS idx_dc_member_con_code ON dc_member(con_code);

-- 表注释
COMMENT ON TABLE dc_member IS '东方财富板块每日成分数据（Tushare dc_member接口，6000积分/次，单次最大5000条）';
COMMENT ON COLUMN dc_member.trade_date IS '交易日期（YYYYMMDD格式）';
COMMENT ON COLUMN dc_member.ts_code IS '概念板块代码（如 BK1184.DC）';
COMMENT ON COLUMN dc_member.con_code IS '成分股票代码（如 002117.SZ）';
COMMENT ON COLUMN dc_member.name IS '成分股名称';
