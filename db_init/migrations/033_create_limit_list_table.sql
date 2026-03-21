-- 创建涨跌停列表表
-- Tushare 接口: limit_list_d
-- 描述: 获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）

CREATE TABLE IF NOT EXISTS limit_list_d (
    -- 主键字段
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,

    -- 基础信息
    industry VARCHAR(50),
    name VARCHAR(50),

    -- 行情数据
    close DECIMAL(10, 2),
    pct_chg DECIMAL(10, 2),
    amount DECIMAL(20, 2),
    limit_amount DECIMAL(20, 2),

    -- 市值数据
    float_mv DECIMAL(20, 2),
    total_mv DECIMAL(20, 2),
    turnover_ratio DECIMAL(10, 2),

    -- 封板数据
    fd_amount DECIMAL(20, 2),
    first_time VARCHAR(10),
    last_time VARCHAR(10),
    open_times INT,

    -- 统计数据
    up_stat VARCHAR(20),
    limit_times INT,
    limit_type VARCHAR(1),

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 主键和索引
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_limit_list_trade_date ON limit_list_d(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_limit_list_ts_code ON limit_list_d(ts_code);
CREATE INDEX IF NOT EXISTS idx_limit_list_limit_type ON limit_list_d(limit_type);
CREATE INDEX IF NOT EXISTS idx_limit_list_limit_times ON limit_list_d(limit_times);

-- 添加表注释
COMMENT ON TABLE limit_list_d IS 'Tushare涨跌停列表数据（limit_list_d）- 每日涨跌停、炸板数据，数据从2020年开始';
COMMENT ON COLUMN limit_list_d.trade_date IS '交易日期';
COMMENT ON COLUMN limit_list_d.ts_code IS '股票代码';
COMMENT ON COLUMN limit_list_d.industry IS '所属行业';
COMMENT ON COLUMN limit_list_d.name IS '股票名称';
COMMENT ON COLUMN limit_list_d.close IS '收盘价';
COMMENT ON COLUMN limit_list_d.pct_chg IS '涨跌幅';
COMMENT ON COLUMN limit_list_d.amount IS '成交额';
COMMENT ON COLUMN limit_list_d.limit_amount IS '板上成交金额(跌停)';
COMMENT ON COLUMN limit_list_d.float_mv IS '流通市值';
COMMENT ON COLUMN limit_list_d.total_mv IS '总市值';
COMMENT ON COLUMN limit_list_d.turnover_ratio IS '换手率';
COMMENT ON COLUMN limit_list_d.fd_amount IS '封单金额';
COMMENT ON COLUMN limit_list_d.first_time IS '首次封板时间';
COMMENT ON COLUMN limit_list_d.last_time IS '最后封板时间';
COMMENT ON COLUMN limit_list_d.open_times IS '炸板次数';
COMMENT ON COLUMN limit_list_d.up_stat IS '涨停统计';
COMMENT ON COLUMN limit_list_d.limit_times IS '连板数';
COMMENT ON COLUMN limit_list_d.limit_type IS 'D跌停U涨停Z炸板';
