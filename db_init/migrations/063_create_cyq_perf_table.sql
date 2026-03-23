-- 创建每日筹码及胜率表
-- Tushare接口: cyq_perf
-- 描述: A股每日筹码平均成本和胜率情况
-- 限制: 单次最大5000条
-- 积分: 5000积分/天20000次, 10000积分/天200000次, 15000积分/天不限

CREATE TABLE IF NOT EXISTS cyq_perf (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,

    -- 价格区间
    his_low NUMERIC(10, 2),
    his_high NUMERIC(10, 2),

    -- 成本分位数
    cost_5pct NUMERIC(10, 2),
    cost_15pct NUMERIC(10, 2),
    cost_50pct NUMERIC(10, 2),
    cost_85pct NUMERIC(10, 2),
    cost_95pct NUMERIC(10, 2),

    -- 加权平均成本
    weight_avg NUMERIC(10, 2),

    -- 胜率 (%)
    winner_rate NUMERIC(10, 2),

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_cyq_perf_ts_code ON cyq_perf(ts_code);
CREATE INDEX IF NOT EXISTS idx_cyq_perf_trade_date ON cyq_perf(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_cyq_perf_date_code ON cyq_perf(trade_date DESC, ts_code);

-- 添加表注释
COMMENT ON TABLE cyq_perf IS 'Tushare-每日筹码及胜率数据';
COMMENT ON COLUMN cyq_perf.ts_code IS '股票代码';
COMMENT ON COLUMN cyq_perf.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN cyq_perf.his_low IS '历史最低价';
COMMENT ON COLUMN cyq_perf.his_high IS '历史最高价';
COMMENT ON COLUMN cyq_perf.cost_5pct IS '5分位成本';
COMMENT ON COLUMN cyq_perf.cost_15pct IS '15分位成本';
COMMENT ON COLUMN cyq_perf.cost_50pct IS '50分位成本（中位数）';
COMMENT ON COLUMN cyq_perf.cost_85pct IS '85分位成本';
COMMENT ON COLUMN cyq_perf.cost_95pct IS '95分位成本';
COMMENT ON COLUMN cyq_perf.weight_avg IS '加权平均成本';
COMMENT ON COLUMN cyq_perf.winner_rate IS '胜率 (%)';
