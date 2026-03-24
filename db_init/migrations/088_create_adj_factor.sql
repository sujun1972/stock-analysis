-- 创建复权因子表
-- Tushare 接口: adj_factor
-- 描述: 获取股票复权因子，可提取单只股票全部历史复权因子，也可以提取单日全部股票的复权因子
-- 更新时间: 盘前9点15~20分完成当日复权因子入库
-- 积分要求: 2000积分起，5000以上可高频调取

CREATE TABLE IF NOT EXISTS adj_factor (
    ts_code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,
    adj_factor DECIMAL(20, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_adj_factor_trade_date ON adj_factor(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_adj_factor_ts_code ON adj_factor(ts_code);

-- 添加表注释
COMMENT ON TABLE adj_factor IS '股票复权因子数据（Tushare adj_factor接口，2000积分/次）';
COMMENT ON COLUMN adj_factor.ts_code IS '股票代码';
COMMENT ON COLUMN adj_factor.trade_date IS '交易日期 YYYYMMDD';
COMMENT ON COLUMN adj_factor.adj_factor IS '复权因子';
COMMENT ON COLUMN adj_factor.created_at IS '创建时间';
COMMENT ON COLUMN adj_factor.updated_at IS '更新时间';
