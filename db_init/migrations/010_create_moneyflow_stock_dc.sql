-- =====================================================
-- 个股资金流向表（东方财富DC数据）
-- 创建时间：2026-03-19
-- 接口：moneyflow_dc
-- 说明：东方财富个股资金流向数据，每日盘后更新
-- 数据开始时间：20230911
-- 积分：5000积分，单次最大6000条
-- =====================================================

CREATE TABLE IF NOT EXISTS moneyflow_stock_dc (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期 YYYYMMDD
    ts_code VARCHAR(10) NOT NULL,             -- 股票代码
    name VARCHAR(50),                         -- 股票名称
    pct_change DECIMAL(10,4),                 -- 涨跌幅(%)
    close DECIMAL(10,2),                      -- 最新价（元）
    net_amount DECIMAL(20,4),                 -- 今日主力净流入额（万元）
    net_amount_rate DECIMAL(10,4),            -- 今日主力净流入净占比(%)
    buy_elg_amount DECIMAL(20,4),             -- 今日超大单净流入额（万元）
    buy_elg_amount_rate DECIMAL(10,4),        -- 今日超大单净流入占比(%)
    buy_lg_amount DECIMAL(20,4),              -- 今日大单净流入额（万元）
    buy_lg_amount_rate DECIMAL(10,4),         -- 今日大单净流入占比(%)
    buy_md_amount DECIMAL(20,4),              -- 今日中单净流入额（万元）
    buy_md_amount_rate DECIMAL(10,4),         -- 今日中单净流入占比(%)
    buy_sm_amount DECIMAL(20,4),              -- 今日小单净流入额（万元）
    buy_sm_amount_rate DECIMAL(10,4),         -- 今日小单净流入占比(%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date, ts_code)
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_moneyflow_stock_dc_trade_date ON moneyflow_stock_dc(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_stock_dc_ts_code ON moneyflow_stock_dc(ts_code);
CREATE INDEX IF NOT EXISTS idx_moneyflow_stock_dc_net_amount ON moneyflow_stock_dc(net_amount DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_stock_dc_net_amount_rate ON moneyflow_stock_dc(net_amount_rate DESC);

-- 尝试创建TimescaleDB hypertable（如果可用）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        IF NOT EXISTS (
            SELECT 1 FROM timescaledb_information.hypertables
            WHERE table_name = 'moneyflow_stock_dc'
        ) THEN
            -- 先将 trade_date 转换为日期类型的临时列
            ALTER TABLE moneyflow_stock_dc ADD COLUMN IF NOT EXISTS trade_date_ts DATE;
            UPDATE moneyflow_stock_dc SET trade_date_ts = TO_DATE(trade_date, 'YYYYMMDD');

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
COMMENT ON TABLE moneyflow_stock_dc IS '东方财富个股资金流向数据表（DC），每日盘后更新，数据开始于20230911';
COMMENT ON COLUMN moneyflow_stock_dc.trade_date IS '交易日期，格式：YYYYMMDD';
COMMENT ON COLUMN moneyflow_stock_dc.ts_code IS '股票代码';
COMMENT ON COLUMN moneyflow_stock_dc.name IS '股票名称';
COMMENT ON COLUMN moneyflow_stock_dc.pct_change IS '涨跌幅(%)';
COMMENT ON COLUMN moneyflow_stock_dc.close IS '最新价（元）';
COMMENT ON COLUMN moneyflow_stock_dc.net_amount IS '今日主力净流入额（万元）';
COMMENT ON COLUMN moneyflow_stock_dc.net_amount_rate IS '今日主力净流入净占比(%)';
COMMENT ON COLUMN moneyflow_stock_dc.buy_elg_amount IS '今日超大单净流入额（万元）';
COMMENT ON COLUMN moneyflow_stock_dc.buy_elg_amount_rate IS '今日超大单净流入占比(%)';
COMMENT ON COLUMN moneyflow_stock_dc.buy_lg_amount IS '今日大单净流入额（万元）';
COMMENT ON COLUMN moneyflow_stock_dc.buy_lg_amount_rate IS '今日大单净流入占比(%)';
COMMENT ON COLUMN moneyflow_stock_dc.buy_md_amount IS '今日中单净流入额（万元）';
COMMENT ON COLUMN moneyflow_stock_dc.buy_md_amount_rate IS '今日中单净流入占比(%)';
COMMENT ON COLUMN moneyflow_stock_dc.buy_sm_amount IS '今日小单净流入额（万元）';
COMMENT ON COLUMN moneyflow_stock_dc.buy_sm_amount_rate IS '今日小单净流入占比(%)';

-- 输出创建完成信息
DO $$
BEGIN
    RAISE NOTICE '个股资金流向表 moneyflow_stock_dc 创建完成';
END $$;
