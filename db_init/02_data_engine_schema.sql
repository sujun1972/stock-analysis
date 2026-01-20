-- ================================================
-- Data Engine Schema
-- A股AI交易系统 - 数据获取与管理引擎
-- ================================================

-- 1. 系统配置表
-- 存储数据源选择、Tushare Token 等全局配置
CREATE TABLE IF NOT EXISTS system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, description)
VALUES
    ('data_source', 'akshare', '当前数据源: akshare 或 tushare'),
    ('tushare_token', '', 'Tushare API Token'),
    ('sync_status', 'idle', '同步状态: idle, running, completed, failed'),
    ('last_sync_date', '', '最后同步日期'),
    ('sync_progress', '0', '同步进度百分比 (0-100)'),
    ('sync_total', '0', '总同步条数'),
    ('sync_completed', '0', '已完成条数')
ON CONFLICT (config_key) DO NOTHING;

-- 2. 股票基本信息表 (优化版)
-- 存储全量 A 股列表及上市状态
CREATE TABLE IF NOT EXISTS stock_basic (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,           -- 股票代码 (统一格式: 000001)
    name VARCHAR(50) NOT NULL,                  -- 股票名称
    market VARCHAR(20),                         -- 市场类型 (上海主板/深圳主板/创业板/科创板)
    industry VARCHAR(50),                       -- 行业
    area VARCHAR(50),                           -- 地区
    list_date DATE,                             -- 上市日期
    delist_date DATE,                           -- 退市日期
    status VARCHAR(20) DEFAULT '正常',          -- 状态: 正常/停牌/退市
    data_source VARCHAR(20) DEFAULT 'akshare',  -- 数据来源
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引优化
    CONSTRAINT unique_stock_code UNIQUE (code)
);

CREATE INDEX IF NOT EXISTS idx_stock_basic_market ON stock_basic(market);
CREATE INDEX IF NOT EXISTS idx_stock_basic_status ON stock_basic(status);
CREATE INDEX IF NOT EXISTS idx_stock_basic_industry ON stock_basic(industry);

-- 3. 日线数据表 (使用 TimescaleDB Hypertable)
-- 存储历史日线数据 (OHLCV)
CREATE TABLE IF NOT EXISTS stock_daily (
    code VARCHAR(10) NOT NULL,                  -- 股票代码
    trade_date DATE NOT NULL,                   -- 交易日期
    open NUMERIC(12, 3),                        -- 开盘价
    high NUMERIC(12, 3),                        -- 最高价
    low NUMERIC(12, 3),                         -- 最低价
    close NUMERIC(12, 3),                       -- 收盘价
    volume BIGINT,                              -- 成交量
    amount NUMERIC(20, 2),                      -- 成交额
    amplitude NUMERIC(10, 3),                   -- 振幅
    pct_change NUMERIC(10, 3),                  -- 涨跌幅
    change_amount NUMERIC(12, 3),               -- 涨跌额
    turnover NUMERIC(10, 3),                    -- 换手率
    data_source VARCHAR(20) DEFAULT 'akshare',  -- 数据来源
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 联合主键
    PRIMARY KEY (code, trade_date)
);

-- 将 stock_daily 转换为 TimescaleDB Hypertable (按日期分区)
SELECT create_hypertable(
    'stock_daily',
    'trade_date',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '1 month'
);

-- 创建复合索引优化查询
CREATE INDEX IF NOT EXISTS idx_stock_daily_code_date ON stock_daily(code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_daily_date ON stock_daily(trade_date DESC);

-- 4. 分时数据表 (1/5/15/30/60分钟)
-- 存储分时K线数据
CREATE TABLE IF NOT EXISTS stock_min (
    code VARCHAR(10) NOT NULL,                  -- 股票代码
    trade_time TIMESTAMP NOT NULL,              -- 交易时间
    period VARCHAR(5) NOT NULL,                 -- 周期: 1/5/15/30/60
    open NUMERIC(12, 3),                        -- 开盘价
    high NUMERIC(12, 3),                        -- 最高价
    low NUMERIC(12, 3),                         -- 最低价
    close NUMERIC(12, 3),                       -- 收盘价
    volume BIGINT,                              -- 成交量
    amount NUMERIC(20, 2),                      -- 成交额
    amplitude NUMERIC(10, 3),                   -- 振幅
    pct_change NUMERIC(10, 3),                  -- 涨跌幅
    change_amount NUMERIC(12, 3),               -- 涨跌额
    turnover NUMERIC(10, 3),                    -- 换手率
    data_source VARCHAR(20) DEFAULT 'akshare',  -- 数据来源
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 联合主键
    PRIMARY KEY (code, trade_time, period)
);

-- 将 stock_min 转换为 TimescaleDB Hypertable (按时间分区)
SELECT create_hypertable(
    'stock_min',
    'trade_time',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

-- 创建复合索引
CREATE INDEX IF NOT EXISTS idx_stock_min_code_time ON stock_min(code, trade_time DESC);
CREATE INDEX IF NOT EXISTS idx_stock_min_period ON stock_min(period);

-- 5. 实时行情表 (快照表)
-- 存储最新的实时行情数据
CREATE TABLE IF NOT EXISTS stock_realtime (
    code VARCHAR(10) PRIMARY KEY,               -- 股票代码
    name VARCHAR(50),                           -- 股票名称
    latest_price NUMERIC(12, 3),                -- 最新价
    open NUMERIC(12, 3),                        -- 开盘价
    high NUMERIC(12, 3),                        -- 最高价
    low NUMERIC(12, 3),                         -- 最低价
    pre_close NUMERIC(12, 3),                   -- 昨收价
    volume BIGINT,                              -- 成交量
    amount NUMERIC(20, 2),                      -- 成交额
    pct_change NUMERIC(10, 3),                  -- 涨跌幅
    change_amount NUMERIC(12, 3),               -- 涨跌额
    turnover NUMERIC(10, 3),                    -- 换手率
    amplitude NUMERIC(10, 3),                   -- 振幅
    trade_time TIMESTAMP,                       -- 行情时间
    data_source VARCHAR(20) DEFAULT 'akshare',  -- 数据来源
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_realtime_pct_change ON stock_realtime(pct_change DESC);
CREATE INDEX IF NOT EXISTS idx_realtime_volume ON stock_realtime(volume DESC);

-- 6. 数据同步日志表
-- 记录每次同步任务的详细信息
CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) UNIQUE NOT NULL,        -- 任务ID
    task_type VARCHAR(20) NOT NULL,             -- 任务类型: full_sync, incremental, realtime
    data_type VARCHAR(20) NOT NULL,             -- 数据类型: daily, minute, realtime
    data_source VARCHAR(20) NOT NULL,           -- 数据源
    status VARCHAR(20) NOT NULL,                -- 状态: running, completed, failed
    total_count INTEGER DEFAULT 0,              -- 总数
    success_count INTEGER DEFAULT 0,            -- 成功数
    failed_count INTEGER DEFAULT 0,             -- 失败数
    progress INTEGER DEFAULT 0,                 -- 进度 (0-100)
    error_message TEXT,                         -- 错误信息
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

CREATE INDEX IF NOT EXISTS idx_sync_log_task_id ON sync_log(task_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON sync_log(status);
CREATE INDEX IF NOT EXISTS idx_sync_log_started ON sync_log(started_at DESC);

-- 7. 同步断点表 (用于断点续传)
-- 记录每个股票的同步进度
CREATE TABLE IF NOT EXISTS sync_checkpoint (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(50) NOT NULL,               -- 关联任务ID
    code VARCHAR(10) NOT NULL,                  -- 股票代码
    last_sync_date DATE,                        -- 最后同步日期
    sync_status VARCHAR(20),                    -- 同步状态: pending, completed, failed
    error_message TEXT,                         -- 错误信息
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (task_id, code)
);

CREATE INDEX IF NOT EXISTS idx_checkpoint_task ON sync_checkpoint(task_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_status ON sync_checkpoint(sync_status);

-- 8. 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为各表创建触发器
DROP TRIGGER IF EXISTS update_system_config_updated_at ON system_config;
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_stock_basic_updated_at ON stock_basic;
CREATE TRIGGER update_stock_basic_updated_at BEFORE UPDATE ON stock_basic
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_stock_realtime_updated_at ON stock_realtime;
CREATE TRIGGER update_stock_realtime_updated_at BEFORE UPDATE ON stock_realtime
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 9. 视图：同步状态概览
CREATE OR REPLACE VIEW v_sync_status AS
SELECT
    config_key,
    config_value,
    description,
    updated_at
FROM system_config
WHERE config_key IN ('data_source', 'sync_status', 'last_sync_date', 'sync_progress', 'sync_total', 'sync_completed');

-- 10. 视图：最近同步任务
CREATE OR REPLACE VIEW v_recent_sync_tasks AS
SELECT
    task_id,
    task_type,
    data_type,
    data_source,
    status,
    total_count,
    success_count,
    failed_count,
    progress,
    started_at,
    completed_at,
    duration_seconds,
    CASE
        WHEN duration_seconds IS NOT NULL AND duration_seconds > 0
        THEN ROUND(success_count::NUMERIC / duration_seconds, 2)
        ELSE 0
    END as records_per_second
FROM sync_log
ORDER BY started_at DESC
LIMIT 20;

-- 完成
COMMENT ON TABLE system_config IS '系统全局配置表';
COMMENT ON TABLE stock_basic IS '股票基本信息表';
COMMENT ON TABLE stock_daily IS '日线数据表 (TimescaleDB Hypertable)';
COMMENT ON TABLE stock_min IS '分时数据表 (TimescaleDB Hypertable)';
COMMENT ON TABLE stock_realtime IS '实时行情快照表';
COMMENT ON TABLE sync_log IS '数据同步日志表';
COMMENT ON TABLE sync_checkpoint IS '同步断点续传表';
