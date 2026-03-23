-- 创建神奇九转指标表
-- Tushare接口: stk_nineturn
-- 描述: 神奇九转(又称"九转序列")是一种基于技术分析的股票趋势反转指标
-- 权限: 需要6000积分
-- 限量: 单次提取最大返回10000行数据
-- 数据起始: 20230101

CREATE TABLE IF NOT EXISTS stk_nineturn (
    ts_code VARCHAR(10) NOT NULL,           -- 股票代码
    trade_date TIMESTAMP NOT NULL,          -- 交易日期
    freq VARCHAR(10) DEFAULT 'daily',       -- 频率(日daily)
    open NUMERIC(10, 2),                    -- 开盘价
    high NUMERIC(10, 2),                    -- 最高价
    low NUMERIC(10, 2),                     -- 最低价
    close NUMERIC(10, 2),                   -- 收盘价
    vol NUMERIC(20, 2),                     -- 成交量
    amount NUMERIC(20, 2),                  -- 成交额
    up_count NUMERIC(5, 2),                 -- 上九转计数
    down_count NUMERIC(5, 2),               -- 下九转计数
    nine_up_turn VARCHAR(10),               -- 是否上九转(+9表示上九转)
    nine_down_turn VARCHAR(10),             -- 是否下九转(-9表示下九转)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date, freq)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_stk_nineturn_trade_date ON stk_nineturn(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stk_nineturn_ts_code ON stk_nineturn(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_nineturn_up_turn ON stk_nineturn(nine_up_turn) WHERE nine_up_turn = '+9';
CREATE INDEX IF NOT EXISTS idx_stk_nineturn_down_turn ON stk_nineturn(nine_down_turn) WHERE nine_down_turn = '-9';

-- 添加表注释
COMMENT ON TABLE stk_nineturn IS 'Tushare神奇九转指标-用于识别股价潜在反转点(6000积分/次,数据从2023年开始)';
COMMENT ON COLUMN stk_nineturn.ts_code IS '股票代码';
COMMENT ON COLUMN stk_nineturn.trade_date IS '交易日期';
COMMENT ON COLUMN stk_nineturn.freq IS '频率(日daily)';
COMMENT ON COLUMN stk_nineturn.open IS '开盘价';
COMMENT ON COLUMN stk_nineturn.high IS '最高价';
COMMENT ON COLUMN stk_nineturn.low IS '最低价';
COMMENT ON COLUMN stk_nineturn.close IS '收盘价';
COMMENT ON COLUMN stk_nineturn.vol IS '成交量';
COMMENT ON COLUMN stk_nineturn.amount IS '成交额';
COMMENT ON COLUMN stk_nineturn.up_count IS '上九转计数';
COMMENT ON COLUMN stk_nineturn.down_count IS '下九转计数';
COMMENT ON COLUMN stk_nineturn.nine_up_turn IS '是否上九转(+9表示上九转)';
COMMENT ON COLUMN stk_nineturn.nine_down_turn IS '是否下九转(-9表示下九转)';
