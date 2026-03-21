-- 创建交易所重点提示证券表
CREATE TABLE IF NOT EXISTS stk_alert (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    start_date VARCHAR(8) NOT NULL,

    -- 基础信息字段
    name VARCHAR(50),
    end_date VARCHAR(8),
    type VARCHAR(50),

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 联合主键
    PRIMARY KEY (ts_code, start_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_alert_start_date ON stk_alert(start_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_alert_end_date ON stk_alert(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_alert_ts_code ON stk_alert(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_alert_type ON stk_alert(type);

-- 添加表注释
COMMENT ON TABLE stk_alert IS '交易所重点提示证券（Tushare stk_alert接口）- 根据证券交易所交易规则，交易所每日发布重点提示证券';

-- 添加字段注释
COMMENT ON COLUMN stk_alert.ts_code IS '股票代码';
COMMENT ON COLUMN stk_alert.name IS '股票名称';
COMMENT ON COLUMN stk_alert.start_date IS '交易所重点提示起始日期（YYYYMMDD）';
COMMENT ON COLUMN stk_alert.end_date IS '交易所重点提示参考截至日期（YYYYMMDD）';
COMMENT ON COLUMN stk_alert.type IS '提示类型';
