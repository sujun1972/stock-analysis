-- 业绩预告数据表
-- Tushare 接口: forecast_vip
-- 描述: 获取业绩预告数据
-- 权限: 用户需要至少2000积分才可以调取

CREATE TABLE IF NOT EXISTS forecast (
    ts_code VARCHAR(10) NOT NULL,
    ann_date VARCHAR(8) NOT NULL,
    end_date VARCHAR(8) NOT NULL,
    type VARCHAR(20),
    p_change_min DECIMAL(20, 4),
    p_change_max DECIMAL(20, 4),
    net_profit_min DECIMAL(20, 4),
    net_profit_max DECIMAL(20, 4),
    last_parent_net DECIMAL(20, 4),
    first_ann_date VARCHAR(8),
    summary TEXT,
    change_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, ann_date, end_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_forecast_ann_date ON forecast(ann_date DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_end_date ON forecast(end_date DESC);
CREATE INDEX IF NOT EXISTS idx_forecast_ts_code ON forecast(ts_code);
CREATE INDEX IF NOT EXISTS idx_forecast_type ON forecast(type);

-- 添加表注释
COMMENT ON TABLE forecast IS '业绩预告数据 (Tushare forecast_vip接口, 2000积分)';
COMMENT ON COLUMN forecast.ts_code IS 'TS股票代码';
COMMENT ON COLUMN forecast.ann_date IS '公告日期 (YYYYMMDD)';
COMMENT ON COLUMN forecast.end_date IS '报告期 (YYYYMMDD，每个季度最后一天)';
COMMENT ON COLUMN forecast.type IS '业绩预告类型(预增/预减/扭亏/首亏/续亏/续盈/略增/略减)';
COMMENT ON COLUMN forecast.p_change_min IS '预告净利润变动幅度下限（%）';
COMMENT ON COLUMN forecast.p_change_max IS '预告净利润变动幅度上限（%）';
COMMENT ON COLUMN forecast.net_profit_min IS '预告净利润下限（万元）';
COMMENT ON COLUMN forecast.net_profit_max IS '预告净利润上限（万元）';
COMMENT ON COLUMN forecast.last_parent_net IS '上年同期归属母公司净利润（万元）';
COMMENT ON COLUMN forecast.first_ann_date IS '首次公告日 (YYYYMMDD)';
COMMENT ON COLUMN forecast.summary IS '业绩预告摘要';
COMMENT ON COLUMN forecast.change_reason IS '业绩变动原因';
