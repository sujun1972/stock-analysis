-- 个股资金流向表（Tushare标准接口）
-- 数据源：Tushare pro.moneyflow()
-- 说明：获取沪深A股票资金流向数据，分析大单小单成交情况
-- 积分消耗：2000积分/次
-- 更新频率：每日17:30更新
-- 数据起始：2010年
-- 与 moneyflow_stock_dc 的区别：
--   - moneyflow_stock_dc: 东方财富DC数据源（pro.moneyflow_dc），净流入为核心指标
--   - moneyflow: Tushare标准接口（pro.moneyflow），买卖量/额分别记录

CREATE TABLE IF NOT EXISTS moneyflow (
    -- 主键字段
    ts_code VARCHAR(10) NOT NULL,
    trade_date VARCHAR(8) NOT NULL,  -- 交易日期 YYYYMMDD 格式

    -- 小单数据（<5万）
    buy_sm_vol BIGINT DEFAULT 0,                -- 小单买入量（手）
    buy_sm_amount DECIMAL(20, 4) DEFAULT 0,     -- 小单买入金额（万元）
    sell_sm_vol BIGINT DEFAULT 0,               -- 小单卖出量（手）
    sell_sm_amount DECIMAL(20, 4) DEFAULT 0,    -- 小单卖出金额（万元）

    -- 中单数据（5万~20万）
    buy_md_vol BIGINT DEFAULT 0,                -- 中单买入量（手）
    buy_md_amount DECIMAL(20, 4) DEFAULT 0,     -- 中单买入金额（万元）
    sell_md_vol BIGINT DEFAULT 0,               -- 中单卖出量（手）
    sell_md_amount DECIMAL(20, 4) DEFAULT 0,    -- 中单卖出金额（万元）

    -- 大单数据（20万~100万）
    buy_lg_vol BIGINT DEFAULT 0,                -- 大单买入量（手）
    buy_lg_amount DECIMAL(20, 4) DEFAULT 0,     -- 大单买入金额（万元）
    sell_lg_vol BIGINT DEFAULT 0,               -- 大单卖出量（手）
    sell_lg_amount DECIMAL(20, 4) DEFAULT 0,    -- 大单卖出金额（万元）

    -- 特大单数据（>=100万）
    buy_elg_vol BIGINT DEFAULT 0,               -- 特大单买入量（手）
    buy_elg_amount DECIMAL(20, 4) DEFAULT 0,    -- 特大单买入金额（万元）
    sell_elg_vol BIGINT DEFAULT 0,              -- 特大单卖出量（手）
    sell_elg_amount DECIMAL(20, 4) DEFAULT 0,   -- 特大单卖出金额（万元）

    -- 汇总数据
    net_mf_vol BIGINT DEFAULT 0,                -- 净流入量（手）
    net_mf_amount DECIMAL(20, 4) DEFAULT 0,     -- 净流入额（万元）

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 主键
    PRIMARY KEY (ts_code, trade_date)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_moneyflow_trade_date ON moneyflow (trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ts_code ON moneyflow (ts_code);
CREATE INDEX IF NOT EXISTS idx_moneyflow_net_mf_amount ON moneyflow (net_mf_amount DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_date_amount ON moneyflow (trade_date DESC, net_mf_amount DESC);

-- 添加表注释
COMMENT ON TABLE moneyflow IS '个股资金流向数据（Tushare标准接口 pro.moneyflow）- 基于主动买卖单统计的资金流向，包含小单/中单/大单/特大单的买卖量和买卖额';
