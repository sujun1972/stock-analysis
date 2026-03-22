-- 创建主营业务构成表
CREATE TABLE IF NOT EXISTS fina_mainbz (
    ts_code VARCHAR(20) NOT NULL,           -- TS代码
    end_date VARCHAR(8) NOT NULL,           -- 报告期(YYYYMMDD)
    bz_item VARCHAR(100) NOT NULL,          -- 主营业务来源
    bz_sales NUMERIC(20, 2),                -- 主营业务收入(元)
    bz_profit NUMERIC(20, 2),               -- 主营业务利润(元)
    bz_cost NUMERIC(20, 2),                 -- 主营业务成本(元)
    curr_type VARCHAR(20),                  -- 货币代码
    update_flag VARCHAR(1),                 -- 是否更新
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, end_date, bz_item)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_fina_mainbz_ts_code ON fina_mainbz(ts_code);
CREATE INDEX IF NOT EXISTS idx_fina_mainbz_end_date ON fina_mainbz(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_fina_mainbz_date_code ON fina_mainbz(end_date, ts_code);

-- 添加表注释
COMMENT ON TABLE fina_mainbz IS 'Tushare接口：上市公司主营业务构成数据（分产品/地区/行业）';
COMMENT ON COLUMN fina_mainbz.ts_code IS 'TS代码';
COMMENT ON COLUMN fina_mainbz.end_date IS '报告期(YYYYMMDD)';
COMMENT ON COLUMN fina_mainbz.bz_item IS '主营业务来源';
COMMENT ON COLUMN fina_mainbz.bz_sales IS '主营业务收入(元)';
COMMENT ON COLUMN fina_mainbz.bz_profit IS '主营业务利润(元)';
COMMENT ON COLUMN fina_mainbz.bz_cost IS '主营业务成本(元)';
COMMENT ON COLUMN fina_mainbz.curr_type IS '货币代码';
COMMENT ON COLUMN fina_mainbz.update_flag IS '是否更新';
