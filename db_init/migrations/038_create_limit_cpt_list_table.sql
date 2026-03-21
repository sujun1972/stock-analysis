-- 创建最强板块统计表 (limit_cpt_list)
-- Tushare 接口: limit_cpt_list
-- 描述: 获取每天涨停股票最多最强的概念板块

CREATE TABLE IF NOT EXISTS limit_cpt_list (
    trade_date VARCHAR(8) NOT NULL,        -- 交易日期（YYYYMMDD）
    ts_code VARCHAR(20) NOT NULL,          -- 板块代码
    name VARCHAR(100),                     -- 板块名称
    days INTEGER,                          -- 上榜天数
    up_stat VARCHAR(20),                   -- 连板高度（如：9天7板）
    cons_nums INTEGER,                     -- 连板家数
    up_nums INTEGER,                       -- 涨停家数
    pct_chg NUMERIC(10, 4),                -- 涨跌幅%
    rank INTEGER,                          -- 板块热点排名
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_limit_cpt_list_trade_date ON limit_cpt_list(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_limit_cpt_list_ts_code ON limit_cpt_list(ts_code);
CREATE INDEX IF NOT EXISTS idx_limit_cpt_list_rank ON limit_cpt_list(trade_date DESC, rank ASC);

-- 添加表注释
COMMENT ON TABLE limit_cpt_list IS 'Tushare 最强板块统计（每天涨停股票最多最强的概念板块）- 积分消耗：8000';
COMMENT ON COLUMN limit_cpt_list.trade_date IS '交易日期（YYYYMMDD）';
COMMENT ON COLUMN limit_cpt_list.ts_code IS '板块代码';
COMMENT ON COLUMN limit_cpt_list.name IS '板块名称';
COMMENT ON COLUMN limit_cpt_list.days IS '上榜天数';
COMMENT ON COLUMN limit_cpt_list.up_stat IS '连板高度（如：9天7板）';
COMMENT ON COLUMN limit_cpt_list.cons_nums IS '连板家数';
COMMENT ON COLUMN limit_cpt_list.up_nums IS '涨停家数';
COMMENT ON COLUMN limit_cpt_list.pct_chg IS '涨跌幅%';
COMMENT ON COLUMN limit_cpt_list.rank IS '板块热点排名';
