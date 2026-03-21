-- 创建股票回购表
CREATE TABLE IF NOT EXISTS repurchase (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8),
    proc VARCHAR(50),
    exp_date VARCHAR(8),
    vol DOUBLE PRECISION,
    amount DOUBLE PRECISION,
    high_limit DOUBLE PRECISION,
    low_limit DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_repurchase_ann_date ON repurchase(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_repurchase_ts_code ON repurchase(ts_code);
CREATE INDEX IF NOT EXISTS idx_repurchase_proc ON repurchase(proc);

-- 添加表注释
COMMENT ON TABLE repurchase IS '上市公司回购股票数据（Tushare接口：repurchase，积分消耗：600）';
COMMENT ON COLUMN repurchase.ts_code IS 'TS代码';
COMMENT ON COLUMN repurchase.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN repurchase.end_date IS '截止日期 YYYYMMDD';
COMMENT ON COLUMN repurchase.proc IS '进度（如：完成、股东大会通过、实施等）';
COMMENT ON COLUMN repurchase.exp_date IS '过期日期 YYYYMMDD';
COMMENT ON COLUMN repurchase.vol IS '回购数量（股）';
COMMENT ON COLUMN repurchase.amount IS '回购金额（元）';
COMMENT ON COLUMN repurchase.high_limit IS '回购最高价（元）';
COMMENT ON COLUMN repurchase.low_limit IS '回购最低价（元）';
