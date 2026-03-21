-- 创建卖方盈利预测数据表
CREATE TABLE IF NOT EXISTS report_rc (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    report_date VARCHAR(8) NOT NULL,
    org_name VARCHAR(100) NOT NULL,
    quarter VARCHAR(10) NOT NULL,

    -- 基础信息字段
    name VARCHAR(50),
    report_title VARCHAR(200),
    report_type VARCHAR(50),
    classify VARCHAR(50),
    author_name VARCHAR(100),

    -- 预测财务指标（单位：万元）
    op_rt DECIMAL(20, 2),      -- 预测营业收入（万元）
    op_pr DECIMAL(20, 2),      -- 预测营业利润（万元）
    tp DECIMAL(20, 2),         -- 预测利润总额（万元）
    np DECIMAL(20, 2),         -- 预测净利润（万元）

    -- 预测估值指标
    eps DECIMAL(10, 4),        -- 预测每股收益（元）
    pe DECIMAL(10, 2),         -- 预测市盈率
    rd DECIMAL(10, 4),         -- 预测股息率
    roe DECIMAL(10, 4),        -- 预测净资产收益率
    ev_ebitda DECIMAL(10, 2),  -- 预测EV/EBITDA

    -- 评级和目标价
    rating VARCHAR(50),        -- 卖方评级
    max_price DECIMAL(10, 2),  -- 预测最高目标价
    min_price DECIMAL(10, 2),  -- 预测最低目标价

    -- 其他字段
    imp_dg VARCHAR(50),        -- 机构关注度
    create_time TIMESTAMP,     -- TS数据更新时间

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 联合主键
    PRIMARY KEY (ts_code, report_date, org_name, quarter)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_report_rc_date ON report_rc(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_report_rc_ts_code ON report_rc(ts_code);
CREATE INDEX IF NOT EXISTS idx_report_rc_org ON report_rc(org_name);
CREATE INDEX IF NOT EXISTS idx_report_rc_quarter ON report_rc(quarter);
CREATE INDEX IF NOT EXISTS idx_report_rc_rating ON report_rc(rating);

-- 添加表注释
COMMENT ON TABLE report_rc IS '卖方盈利预测数据（Tushare report_rc接口）- 券商研报的盈利预测数据，数据从2010年开始';

-- 添加字段注释
COMMENT ON COLUMN report_rc.ts_code IS '股票代码';
COMMENT ON COLUMN report_rc.name IS '股票名称';
COMMENT ON COLUMN report_rc.report_date IS '研报日期（YYYYMMDD）';
COMMENT ON COLUMN report_rc.report_title IS '报告标题';
COMMENT ON COLUMN report_rc.report_type IS '报告类型';
COMMENT ON COLUMN report_rc.classify IS '报告分类';
COMMENT ON COLUMN report_rc.org_name IS '机构名称';
COMMENT ON COLUMN report_rc.author_name IS '作者';
COMMENT ON COLUMN report_rc.quarter IS '预测报告期（如：2024Q4）';
COMMENT ON COLUMN report_rc.op_rt IS '预测营业收入（万元）';
COMMENT ON COLUMN report_rc.op_pr IS '预测营业利润（万元）';
COMMENT ON COLUMN report_rc.tp IS '预测利润总额（万元）';
COMMENT ON COLUMN report_rc.np IS '预测净利润（万元）';
COMMENT ON COLUMN report_rc.eps IS '预测每股收益（元）';
COMMENT ON COLUMN report_rc.pe IS '预测市盈率';
COMMENT ON COLUMN report_rc.rd IS '预测股息率';
COMMENT ON COLUMN report_rc.roe IS '预测净资产收益率';
COMMENT ON COLUMN report_rc.ev_ebitda IS '预测EV/EBITDA';
COMMENT ON COLUMN report_rc.rating IS '卖方评级';
COMMENT ON COLUMN report_rc.max_price IS '预测最高目标价';
COMMENT ON COLUMN report_rc.min_price IS '预测最低目标价';
COMMENT ON COLUMN report_rc.imp_dg IS '机构关注度';
COMMENT ON COLUMN report_rc.create_time IS 'TS数据更新时间';
