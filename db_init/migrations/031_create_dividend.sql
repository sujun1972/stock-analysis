-- 031_create_dividend.sql
-- 分红送股数据表
-- Tushare接口: dividend
-- 权限要求: 2000积分

CREATE TABLE IF NOT EXISTS dividend (
    ts_code VARCHAR(10) NOT NULL,
    end_date VARCHAR(8),
    ann_date VARCHAR(8),
    div_proc VARCHAR(50),
    stk_div NUMERIC(20, 6),
    stk_bo_rate NUMERIC(20, 6),
    stk_co_rate NUMERIC(20, 6),
    cash_div NUMERIC(20, 6),
    cash_div_tax NUMERIC(20, 6),
    record_date VARCHAR(8),
    ex_date VARCHAR(8),
    pay_date VARCHAR(8),
    div_listdate VARCHAR(8),
    imp_ann_date VARCHAR(8),
    base_date VARCHAR(8),
    base_share NUMERIC(20, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, end_date, ann_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_dividend_ts_code ON dividend(ts_code);
CREATE INDEX IF NOT EXISTS idx_dividend_ann_date ON dividend(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_dividend_record_date ON dividend(record_date DESC);
CREATE INDEX IF NOT EXISTS idx_dividend_ex_date ON dividend(ex_date DESC);
CREATE INDEX IF NOT EXISTS idx_dividend_imp_ann_date ON dividend(imp_ann_date DESC);

-- 表注释
COMMENT ON TABLE dividend IS 'Tushare分红送股数据 - 上市公司分红送股详细信息';
