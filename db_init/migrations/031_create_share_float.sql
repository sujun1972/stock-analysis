-- 限售股解禁数据表
-- Tushare接口：share_float
-- 描述：获取限售股解禁信息

CREATE TABLE IF NOT EXISTS share_float (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    float_date VARCHAR(8) NOT NULL,
    float_share NUMERIC(20, 2),
    float_ratio NUMERIC(10, 4),
    holder_name VARCHAR(100),
    share_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, float_date, holder_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_share_float_ts_code ON share_float(ts_code);
CREATE INDEX IF NOT EXISTS idx_share_float_ann_date ON share_float(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_share_float_float_date ON share_float(float_date DESC);

-- 添加表注释
COMMENT ON TABLE share_float IS 'Tushare限售股解禁数据';
COMMENT ON COLUMN share_float.ts_code IS 'TS股票代码';
COMMENT ON COLUMN share_float.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN share_float.float_date IS '解禁日期 YYYYMMDD';
COMMENT ON COLUMN share_float.float_share IS '流通股份(股)';
COMMENT ON COLUMN share_float.float_ratio IS '流通股份占总股本比率';
COMMENT ON COLUMN share_float.holder_name IS '股东名称';
COMMENT ON COLUMN share_float.share_type IS '股份类型';
