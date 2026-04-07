-- 创建机构调研表 (stk_surv)
-- Tushare接口: stk_surv
-- 描述: 获取上市公司机构调研记录数据
-- 积分: 5000积分/次
-- 单次最大: 100条数据

CREATE TABLE IF NOT EXISTS stk_surv (
    -- 主键
    id SERIAL PRIMARY KEY,                   -- 自增主键

    -- 索引字段
    ts_code VARCHAR(10) NOT NULL,            -- TS代码
    surv_date VARCHAR(8) NOT NULL,           -- 调研日期 YYYYMMDD
    fund_visitors TEXT,                       -- 机构参与人员

    -- 数据字段
    name VARCHAR(100),                        -- 股票名称
    rece_place TEXT,                          -- 接待地点
    rece_mode VARCHAR(200),                   -- 接待方式
    rece_org TEXT,                            -- 接待的公司
    org_type VARCHAR(200),                    -- 接待公司类型
    comp_rece TEXT,                           -- 上市公司接待人员
    content TEXT,                             -- 调研内容

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_stk_surv_ts_code ON stk_surv(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_surv_surv_date ON stk_surv(surv_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_surv_org_type ON stk_surv(org_type);
CREATE INDEX IF NOT EXISTS idx_stk_surv_rece_mode ON stk_surv(rece_mode);
CREATE INDEX IF NOT EXISTS idx_stk_surv_composite ON stk_surv(ts_code, surv_date);

-- 唯一约束(防止重复调研记录)
-- 使用MD5哈希fund_visitors来创建唯一约束,因为TEXT类型不能直接用于唯一约束
CREATE UNIQUE INDEX IF NOT EXISTS idx_stk_surv_unique ON stk_surv(ts_code, surv_date, MD5(fund_visitors));

-- 表注释
COMMENT ON TABLE stk_surv IS 'Tushare 机构调研表 - 上市公司机构调研记录数据 (5000积分/次，单次最大100条)';
COMMENT ON COLUMN stk_surv.id IS '自增主键';
COMMENT ON COLUMN stk_surv.ts_code IS 'TS代码';
COMMENT ON COLUMN stk_surv.name IS '股票名称';
COMMENT ON COLUMN stk_surv.surv_date IS '调研日期 YYYYMMDD';
COMMENT ON COLUMN stk_surv.fund_visitors IS '机构参与人员';
COMMENT ON COLUMN stk_surv.rece_place IS '接待地点';
COMMENT ON COLUMN stk_surv.rece_mode IS '接待方式';
COMMENT ON COLUMN stk_surv.rece_org IS '接待的公司';
COMMENT ON COLUMN stk_surv.org_type IS '接待公司类型';
COMMENT ON COLUMN stk_surv.comp_rece IS '上市公司接待人员';
COMMENT ON COLUMN stk_surv.content IS '调研内容';
