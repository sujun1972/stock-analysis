-- =====================================================
-- 大盘资金流向表（东方财富DC数据）
-- 创建时间：2026-03-19
-- 接口：moneyflow_mkt_dc
-- 说明：东方财富大盘资金流向数据，每日盘后更新
-- 积分：120积分试用，6000积分正式调用
-- =====================================================

CREATE TABLE IF NOT EXISTS moneyflow_mkt_dc (
    trade_date VARCHAR(8) NOT NULL,           -- 交易日期 YYYYMMDD
    close_sh DECIMAL(10,2),                   -- 上证收盘价（点）
    pct_change_sh DECIMAL(10,4),              -- 上证涨跌幅(%)
    close_sz DECIMAL(10,2),                   -- 深证收盘价（点）
    pct_change_sz DECIMAL(10,4),              -- 深证涨跌幅(%)
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
);

-- 创建索引以提升查询性能
CREATE INDEX IF NOT EXISTS idx_moneyflow_mkt_dc_trade_date ON moneyflow_mkt_dc(trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_moneyflow_mkt_dc_net_amount ON moneyflow_mkt_dc(net_amount DESC);

-- 尝试创建TimescaleDB hypertable（如果可用）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        IF NOT EXISTS (
            SELECT 1 FROM timescaledb_information.hypertables
            WHERE table_name = 'moneyflow_mkt_dc'
        ) THEN
            -- 先将 trade_date 转换为日期类型的临时列
            ALTER TABLE moneyflow_mkt_dc ADD COLUMN IF NOT EXISTS trade_date_ts DATE;
            UPDATE moneyflow_mkt_dc SET trade_date_ts = TO_DATE(trade_date, 'YYYYMMDD');

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
COMMENT ON TABLE moneyflow_mkt_dc IS '东方财富大盘资金流向数据表（DC），每日盘后更新';
COMMENT ON COLUMN moneyflow_mkt_dc.trade_date IS '交易日期，格式：YYYYMMDD';
COMMENT ON COLUMN moneyflow_mkt_dc.close_sh IS '上证收盘价（点）';
COMMENT ON COLUMN moneyflow_mkt_dc.pct_change_sh IS '上证涨跌幅(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.close_sz IS '深证收盘价（点）';
COMMENT ON COLUMN moneyflow_mkt_dc.pct_change_sz IS '深证涨跌幅(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.net_amount IS '今日主力净流入净额（元）';
COMMENT ON COLUMN moneyflow_mkt_dc.net_amount_rate IS '今日主力净流入净占比(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_elg_amount IS '今日超大单净流入净额（元）';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_elg_amount_rate IS '今日超大单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_lg_amount IS '今日大单净流入净额（元）';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_lg_amount_rate IS '今日大单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_md_amount IS '今日中单净流入净额（元）';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_md_amount_rate IS '今日中单净流入净占比(%)';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_sm_amount IS '今日小单净流入净额（元）';
COMMENT ON COLUMN moneyflow_mkt_dc.buy_sm_amount_rate IS '今日小单净流入净占比(%)';

-- 输出创建完成信息
DO $$
BEGIN
    RAISE NOTICE '大盘资金流向表 moneyflow_mkt_dc 创建完成';
END $$;
