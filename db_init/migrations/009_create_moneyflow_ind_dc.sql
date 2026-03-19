-- =====================================================
-- 板块资金流向表（东财概念及行业板块资金流向 DC）
-- 创建时间：2026-03-19
-- 接口：moneyflow_ind_dc
-- 说明：东方财富板块资金流向数据，每天盘后更新
-- 积分：6000积分调用
-- =====================================================

CREATE TABLE IF NOT EXISTS moneyflow_ind_dc (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期 YYYYMMDD
    content_type VARCHAR(20),                 -- 数据类型(行业、概念、地域)
    ts_code VARCHAR(20) NOT NULL,             -- DC板块代码
    name VARCHAR(100),                        -- 板块名称
    pct_change DECIMAL(10,4),                 -- 板块涨跌幅（%）
    close DECIMAL(10,2),                      -- 板块最新指数
    net_amount DECIMAL(20,4),                 -- 今日主力净流入 净额（元）
    net_amount_rate DECIMAL(10,4),            -- 今日主力净流入净占比%
    buy_elg_amount DECIMAL(20,4),             -- 今日超大单净流入 净额（元）
    buy_elg_amount_rate DECIMAL(10,4),        -- 今日超大单净流入 净占比%
    buy_lg_amount DECIMAL(20,4),              -- 今日大单净流入 净额（元）
    buy_lg_amount_rate DECIMAL(10,4),         -- 今日大单净流入 净占比%
    buy_md_amount DECIMAL(20,4),              -- 今日中单净流入 净额（元）
    buy_md_amount_rate DECIMAL(10,4),         -- 今日中单净流入 净占比%
    buy_sm_amount DECIMAL(20,4),              -- 今日小单净流入 净额（元）
    buy_sm_amount_rate DECIMAL(10,4),         -- 今日小单净流入 净占比%
    buy_sm_amount_stock VARCHAR(20),          -- 今日主力净流入最大股
    rank INT,                                 -- 序号
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_moneyflow_ind_dc_trade_date ON moneyflow_ind_dc(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ind_dc_ts_code ON moneyflow_ind_dc(ts_code);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ind_dc_content_type ON moneyflow_ind_dc(content_type);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ind_dc_net_amount ON moneyflow_ind_dc(net_amount DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_ind_dc_rank ON moneyflow_ind_dc(rank);

-- 尝试创建TimescaleDB hypertable（如果可用）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        IF NOT EXISTS (
            SELECT 1 FROM timescaledb_information.hypertables
            WHERE table_name = 'moneyflow_ind_dc'
        ) THEN
            -- 先将 trade_date 转换为日期类型的临时列
            ALTER TABLE moneyflow_ind_dc ADD COLUMN IF NOT EXISTS trade_date_ts DATE;
            UPDATE moneyflow_ind_dc SET trade_date_ts = TO_DATE(trade_date, 'YYYYMMDD');

            -- 注意：由于主键是 VARCHAR，我们不创建 hypertable
            -- TimescaleDB 需要时间戳类型作为分区键
            RAISE NOTICE 'TimescaleDB hypertable 未创建（主键为 VARCHAR 类型）';
        END IF;
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'TimescaleDB hypertable creation skipped: %', SQLERRM;
END $$;

-- 添加注释
COMMENT ON TABLE moneyflow_ind_dc IS '东财概念及行业板块资金流向数据表（DC），每天盘后更新';
COMMENT ON COLUMN moneyflow_ind_dc.trade_date IS '交易日期，格式：YYYYMMDD';
COMMENT ON COLUMN moneyflow_ind_dc.content_type IS '数据类型(行业、概念、地域)';
COMMENT ON COLUMN moneyflow_ind_dc.ts_code IS 'DC板块代码（行业、概念、地域）';
COMMENT ON COLUMN moneyflow_ind_dc.name IS '板块名称';
COMMENT ON COLUMN moneyflow_ind_dc.pct_change IS '板块涨跌幅（%）';
COMMENT ON COLUMN moneyflow_ind_dc.close IS '板块最新指数';
COMMENT ON COLUMN moneyflow_ind_dc.net_amount IS '今日主力净流入净额（元）';
COMMENT ON COLUMN moneyflow_ind_dc.net_amount_rate IS '今日主力净流入净占比(%)';
COMMENT ON COLUMN moneyflow_ind_dc.buy_elg_amount IS '今日超大单净流入净额（元）';
COMMENT ON COLUMN moneyflow_ind_dc.buy_elg_amount_rate IS '今日超大单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_ind_dc.buy_lg_amount IS '今日大单净流入净额（元）';
COMMENT ON COLUMN moneyflow_ind_dc.buy_lg_amount_rate IS '今日大单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_ind_dc.buy_md_amount IS '今日中单净流入净额（元）';
COMMENT ON COLUMN moneyflow_ind_dc.buy_md_amount_rate IS '今日中单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_ind_dc.buy_sm_amount IS '今日小单净流入净额（元）';
COMMENT ON COLUMN moneyflow_ind_dc.buy_sm_amount_rate IS '今日小单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_ind_dc.buy_sm_amount_stock IS '今日主力净流入最大股';
COMMENT ON COLUMN moneyflow_ind_dc.rank IS '序号';

-- 输出创建完成信息
DO $$
BEGIN
    RAISE NOTICE '板块资金流向表 moneyflow_ind_dc 创建完成';
END $$;
