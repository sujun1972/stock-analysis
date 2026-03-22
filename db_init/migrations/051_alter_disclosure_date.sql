-- 修复财报披露计划表结构
-- 问题：ann_date可能为NULL，但被定义为NOT NULL且在主键中
-- 解决：删除旧表，重新创建正确的表结构

-- 删除旧表
DROP TABLE IF EXISTS disclosure_date CASCADE;

-- 重新创建表（ann_date改为可选，主键调整）
CREATE TABLE IF NOT EXISTS disclosure_date (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8),
    end_date VARCHAR(8) NOT NULL,
    pre_date VARCHAR(8),
    actual_date VARCHAR(8),
    modify_date VARCHAR(8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_disclosure_date_ts_code ON disclosure_date(ts_code);
CREATE INDEX IF NOT EXISTS idx_disclosure_date_end_date ON disclosure_date(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_disclosure_date_ann_date ON disclosure_date(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_disclosure_date_pre_date ON disclosure_date(pre_date DESC);
CREATE INDEX IF NOT EXISTS idx_disclosure_date_actual_date ON disclosure_date(actual_date DESC);

-- 添加表注释
COMMENT ON TABLE disclosure_date IS 'Tushare-财报披露计划日期（500积分/次）';
COMMENT ON COLUMN disclosure_date.ts_code IS 'TS股票代码';
COMMENT ON COLUMN disclosure_date.ann_date IS '最新披露公告日 (YYYYMMDD，可选)';
COMMENT ON COLUMN disclosure_date.end_date IS '报告期（每个季度最后一天，如20181231）';
COMMENT ON COLUMN disclosure_date.pre_date IS '预计披露日期 (YYYYMMDD)';
COMMENT ON COLUMN disclosure_date.actual_date IS '实际披露日期 (YYYYMMDD)';
COMMENT ON COLUMN disclosure_date.modify_date IS '披露日期修正记录';
