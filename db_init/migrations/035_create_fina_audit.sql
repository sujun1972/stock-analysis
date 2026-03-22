-- 创建财务审计意见表
-- Tushare 接口: fina_audit
-- 描述: 获取上市公司定期财务审计意见数据
-- 权限: 用户需要至少500积分才可以调取
-- 更新频率: 定期更新

CREATE TABLE IF NOT EXISTS fina_audit (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8) NOT NULL,
    audit_result VARCHAR(50),
    audit_fees DECIMAL(20, 2),
    audit_agency VARCHAR(200),
    audit_sign VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_fina_audit_ts_code ON fina_audit(ts_code);
CREATE INDEX IF NOT EXISTS idx_fina_audit_ann_date ON fina_audit(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_fina_audit_end_date ON fina_audit(end_date DESC);

-- 添加表注释
COMMENT ON TABLE fina_audit IS '上市公司财务审计意见数据 (Tushare: fina_audit)';
COMMENT ON COLUMN fina_audit.ts_code IS 'TS股票代码';
COMMENT ON COLUMN fina_audit.ann_date IS '公告日期 YYYYMMDD';
COMMENT ON COLUMN fina_audit.end_date IS '报告期 YYYYMMDD (每个季度最后一天的日期)';
COMMENT ON COLUMN fina_audit.audit_result IS '审计结果';
COMMENT ON COLUMN fina_audit.audit_fees IS '审计总费用（元）';
COMMENT ON COLUMN fina_audit.audit_agency IS '会计事务所';
COMMENT ON COLUMN fina_audit.audit_sign IS '签字会计师';
COMMENT ON COLUMN fina_audit.created_at IS '创建时间';
COMMENT ON COLUMN fina_audit.updated_at IS '更新时间';
