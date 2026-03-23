-- 创建券商每月荐股表
-- Tushare接口: broker_recommend
-- 描述: 获取券商月度金股,一般1日~3日内更新当月数据
-- 积分消耗: 6000积分/次
-- 单次限制: 最大1000行

CREATE TABLE IF NOT EXISTS broker_recommend (
    id SERIAL PRIMARY KEY,
    month VARCHAR(6) NOT NULL,
    broker VARCHAR(100) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_month_broker_code UNIQUE (month, broker, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_broker_recommend_month ON broker_recommend(month DESC);
CREATE INDEX IF NOT EXISTS idx_broker_recommend_broker ON broker_recommend(broker);
CREATE INDEX IF NOT EXISTS idx_broker_recommend_ts_code ON broker_recommend(ts_code);

-- 添加表注释和列注释
COMMENT ON TABLE broker_recommend IS 'Tushare券商每月荐股数据,积分消耗6000/次,单次最大1000行';
COMMENT ON COLUMN broker_recommend.month IS '月度 YYYYMM';
COMMENT ON COLUMN broker_recommend.broker IS '券商名称';
COMMENT ON COLUMN broker_recommend.ts_code IS '股票代码';
COMMENT ON COLUMN broker_recommend.name IS '股票简称';
