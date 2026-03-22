-- 创建股东人数表
-- Tushare接口：stk_holdernumber
-- 描述：获取上市公司股东户数数据，数据不定期公布
-- 积分消耗：600积分/次

CREATE TABLE IF NOT EXISTS stk_holdernumber (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8) NOT NULL,
    holder_num INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_holdernumber_ts_code ON stk_holdernumber(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_holdernumber_ann_date ON stk_holdernumber(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_holdernumber_end_date ON stk_holdernumber(end_date DESC);

-- 添加表注释
COMMENT ON TABLE stk_holdernumber IS '股东人数数据（Tushare: stk_holdernumber）';
COMMENT ON COLUMN stk_holdernumber.ts_code IS '股票代码';
COMMENT ON COLUMN stk_holdernumber.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN stk_holdernumber.end_date IS '截止日期 YYYYMMDD';
COMMENT ON COLUMN stk_holdernumber.holder_num IS '股东户数';
COMMENT ON COLUMN stk_holdernumber.created_at IS '创建时间';
COMMENT ON COLUMN stk_holdernumber.updated_at IS '更新时间';
