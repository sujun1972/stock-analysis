-- 创建连板天梯表 (limit_step)
-- 接口: limit_step
-- 描述: 获取每天连板个数晋级的股票，可以分析出每天连续涨停进阶个数，判断强势热度
-- 积分: 8000积分以上每分钟500次，每天总量不限制

CREATE TABLE IF NOT EXISTS limit_step (
    trade_date VARCHAR(8) NOT NULL,
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    nums VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_limit_step_trade_date ON limit_step(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_limit_step_ts_code ON limit_step(ts_code);
CREATE INDEX IF NOT EXISTS idx_limit_step_nums ON limit_step(nums);

-- 添加表注释
COMMENT ON TABLE limit_step IS 'Tushare 连板天梯数据 - 每天连板个数晋级的股票';
COMMENT ON COLUMN limit_step.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN limit_step.ts_code IS '股票代码';
COMMENT ON COLUMN limit_step.name IS '股票名称';
COMMENT ON COLUMN limit_step.nums IS '连板次数';
COMMENT ON COLUMN limit_step.created_at IS '创建时间';
COMMENT ON COLUMN limit_step.updated_at IS '更新时间';
