-- =====================================================
-- Tushare扩展数据表
-- 创建时间：2024-03
-- 说明：补充短线交易所需的关键数据表
-- =====================================================

-- 1. 每日指标表（包含换手率、市盈率等关键指标）
CREATE TABLE IF NOT EXISTS daily_basic (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    close DECIMAL(10,2),           -- 当日收盘价
    turnover_rate DECIMAL(10,4),   -- 换手率（%）
    turnover_rate_f DECIMAL(10,4), -- 换手率（自由流通股）
    volume_ratio DECIMAL(10,4),    -- 量比
    pe DECIMAL(10,4),              -- 市盈率（静态）
    pe_ttm DECIMAL(10,4),          -- 市盈率（TTM）
    pb DECIMAL(10,4),              -- 市净率
    ps DECIMAL(10,4),              -- 市销率（静态）
    ps_ttm DECIMAL(10,4),          -- 市销率（TTM）
    dv_ratio DECIMAL(10,4),        -- 股息率（%）
    dv_ttm DECIMAL(10,4),          -- 股息率（TTM）
    total_share DECIMAL(20,4),     -- 总股本（万股）
    float_share DECIMAL(20,4),     -- 流通股本（万股）
    free_share DECIMAL(20,4),      -- 自由流通股本（万股）
    total_mv DECIMAL(20,4),        -- 总市值（万元）
    circ_mv DECIMAL(20,4),         -- 流通市值（万元）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 2. 个股资金流向表（追踪主力资金动向）
CREATE TABLE IF NOT EXISTS moneyflow (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    buy_sm_vol BIGINT,             -- 小单买入量（手）
    buy_sm_amount DECIMAL(20,4),   -- 小单买入金额（万元）
    sell_sm_vol BIGINT,            -- 小单卖出量
    sell_sm_amount DECIMAL(20,4),  -- 小单卖出金额
    buy_md_vol BIGINT,             -- 中单买入量
    buy_md_amount DECIMAL(20,4),   -- 中单买入金额
    sell_md_vol BIGINT,            -- 中单卖出量
    sell_md_amount DECIMAL(20,4),  -- 中单卖出金额
    buy_lg_vol BIGINT,             -- 大单买入量
    buy_lg_amount DECIMAL(20,4),   -- 大单买入金额
    sell_lg_vol BIGINT,            -- 大单卖出量
    sell_lg_amount DECIMAL(20,4),  -- 大单卖出金额
    buy_elg_vol BIGINT,            -- 特大单买入量
    buy_elg_amount DECIMAL(20,4),  -- 特大单买入金额
    sell_elg_vol BIGINT,           -- 特大单卖出量
    sell_elg_amount DECIMAL(20,4), -- 特大单卖出金额
    net_mf_vol BIGINT,             -- 净流入量（手）
    net_mf_amount DECIMAL(20,4),   -- 净流入额（万元）
    trade_count BIGINT,            -- 交易笔数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 3. 复权因子表（确保价格数据准确性）
CREATE TABLE IF NOT EXISTS adj_factor (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    adj_factor DECIMAL(12,6),      -- 复权因子
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 4. 沪深港通持股表（北向资金）
CREATE TABLE IF NOT EXISTS hk_hold (
    code VARCHAR(10) NOT NULL,     -- 股票代码
    trade_date DATE NOT NULL,
    ts_code VARCHAR(10),           -- TS代码
    name VARCHAR(100),             -- 股票名称
    vol BIGINT,                    -- 持股数量（股）
    ratio DECIMAL(10,4),           -- 持股占比（%）
    exchange VARCHAR(10),          -- 交易所（SH/SZ）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (code, trade_date, exchange)
);

-- 5. 融资融券详细表
CREATE TABLE IF NOT EXISTS margin_detail (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    rzye DECIMAL(20,4),            -- 融资余额（万元）
    rqye DECIMAL(20,4),            -- 融券余额（万元）
    rzmre DECIMAL(20,4),           -- 融资买入额（万元）
    rqyl BIGINT,                   -- 融券余量（股）
    rzche DECIMAL(20,4),           -- 融资偿还额（万元）
    rqchl BIGINT,                  -- 融券偿还量（股）
    rqmcl BIGINT,                  -- 融券卖出量（股）
    rzrqye DECIMAL(20,4),          -- 融资融券余额（万元）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 6. 大宗交易表
CREATE TABLE IF NOT EXISTS block_trade (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    price DECIMAL(10,2),           -- 成交价
    vol DECIMAL(20,4),             -- 成交量（万股）
    amount DECIMAL(20,4),          -- 成交额（万元）
    buyer VARCHAR(200),            -- 买方营业部
    seller VARCHAR(200),           -- 卖方营业部
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 每日涨跌停价格表
CREATE TABLE IF NOT EXISTS stk_limit (
    ts_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    pre_close DECIMAL(10,2),       -- 昨收价
    up_limit DECIMAL(10,2),        -- 涨停价
    down_limit DECIMAL(10,2),      -- 跌停价
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code, trade_date)
);

-- 8. 停复牌信息表
CREATE TABLE IF NOT EXISTS suspend_info (
    id SERIAL PRIMARY KEY,
    ts_code VARCHAR(10) NOT NULL,
    suspend_date DATE,             -- 停牌日期
    resume_date DATE,              -- 复牌日期
    ann_date DATE,                 -- 公告日期
    suspend_reason VARCHAR(500),   -- 停牌原因
    reason_type VARCHAR(50),       -- 停牌原因类型
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. ST股票列表（风险控制）
CREATE TABLE IF NOT EXISTS st_stocks (
    ts_code VARCHAR(10) NOT NULL,
    name VARCHAR(100),
    st_date DATE,                  -- ST日期
    reason VARCHAR(500),           -- ST原因
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ts_code)
);

-- 10. 股权质押表（风险监控）
CREATE TABLE IF NOT EXISTS share_pledge (
    ts_code VARCHAR(10) NOT NULL,
    ann_date DATE NOT NULL,        -- 公告日期
    pledge_ratio DECIMAL(10,4),    -- 质押比例（%）
    pledgor VARCHAR(200),          -- 质押方
    pledgee VARCHAR(200),          -- 质押权人
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建TimescaleDB hypertables以优化时序数据查询
-- 注意：需要先检查TimescaleDB扩展是否已启用
DO $$
BEGIN
    -- 检查并创建TimescaleDB扩展
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        CREATE EXTENSION timescaledb;
    END IF;
END $$;

-- 将表转换为hypertables（如果TimescaleDB可用）
DO $$
BEGIN
    -- daily_basic表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'daily_basic'
    ) THEN
        PERFORM create_hypertable('daily_basic', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- moneyflow表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'moneyflow'
    ) THEN
        PERFORM create_hypertable('moneyflow', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- adj_factor表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'adj_factor'
    ) THEN
        PERFORM create_hypertable('adj_factor', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- hk_hold表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'hk_hold'
    ) THEN
        PERFORM create_hypertable('hk_hold', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- margin_detail表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'margin_detail'
    ) THEN
        PERFORM create_hypertable('margin_detail', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- block_trade表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'block_trade'
    ) THEN
        PERFORM create_hypertable('block_trade', 'trade_date', if_not_exists => TRUE);
    END IF;

    -- stk_limit表
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.hypertables
        WHERE table_name = 'stk_limit'
    ) THEN
        PERFORM create_hypertable('stk_limit', 'trade_date', if_not_exists => TRUE);
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        -- 如果TimescaleDB不可用，继续执行
        RAISE NOTICE 'TimescaleDB hypertables creation skipped: %', SQLERRM;
END $$;

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_daily_basic_ts_code ON daily_basic(ts_code);
CREATE INDEX IF NOT EXISTS idx_daily_basic_turnover ON daily_basic(turnover_rate DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ts_code ON moneyflow(ts_code);
CREATE INDEX IF NOT EXISTS idx_moneyflow_net_amount ON moneyflow(net_mf_amount DESC);
CREATE INDEX IF NOT EXISTS idx_margin_detail_ts_code ON margin_detail(ts_code);
CREATE INDEX IF NOT EXISTS idx_block_trade_ts_code ON block_trade(ts_code);
CREATE INDEX IF NOT EXISTS idx_block_trade_amount ON block_trade(amount DESC);
CREATE INDEX IF NOT EXISTS idx_suspend_info_ts_code ON suspend_info(ts_code);
CREATE INDEX IF NOT EXISTS idx_hk_hold_ts_code ON hk_hold(ts_code);
CREATE INDEX IF NOT EXISTS idx_adj_factor_ts_code ON adj_factor(ts_code);
CREATE INDEX IF NOT EXISTS idx_st_stocks_st_date ON st_stocks(st_date);
CREATE INDEX IF NOT EXISTS idx_share_pledge_ts_code ON share_pledge(ts_code);
CREATE INDEX IF NOT EXISTS idx_stk_limit_ts_code ON stk_limit(ts_code);

-- 添加复合索引以优化常见查询
CREATE INDEX IF NOT EXISTS idx_daily_basic_date_code ON daily_basic(trade_date DESC, ts_code);
CREATE INDEX IF NOT EXISTS idx_moneyflow_date_amount ON moneyflow(trade_date DESC, net_mf_amount DESC);
CREATE INDEX IF NOT EXISTS idx_hk_hold_date_ratio ON hk_hold(trade_date DESC, ratio DESC);
CREATE INDEX IF NOT EXISTS idx_margin_detail_date_rzye ON margin_detail(trade_date DESC, rzye DESC);

-- 添加注释
COMMENT ON TABLE daily_basic IS '每日指标数据表，包含换手率、市盈率等关键指标';
COMMENT ON TABLE moneyflow IS '个股资金流向表，追踪不同级别资金的买卖情况';
COMMENT ON TABLE adj_factor IS '复权因子表，用于价格数据的复权处理';
COMMENT ON TABLE hk_hold IS '沪深港通持股表，追踪北向资金动向';
COMMENT ON TABLE margin_detail IS '融资融券详细数据表';
COMMENT ON TABLE block_trade IS '大宗交易表，追踪机构大额交易';
COMMENT ON TABLE stk_limit IS '涨跌停价格表，提供每日价格限制参考';
COMMENT ON TABLE suspend_info IS '停复牌信息表，用于风险控制';
COMMENT ON TABLE st_stocks IS 'ST股票列表，用于风险控制';
COMMENT ON TABLE share_pledge IS '股权质押表，监控质押风险';

-- 输出创建完成信息
DO $$
BEGIN
    RAISE NOTICE 'Tushare扩展数据表创建完成';
    RAISE NOTICE '已创建10个新表：daily_basic, moneyflow, adj_factor, hk_hold, margin_detail, block_trade, stk_limit, suspend_info, st_stocks, share_pledge';
END $$;