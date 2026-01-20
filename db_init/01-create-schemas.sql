-- 创建扩展
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- 创建股票基本信息表
CREATE TABLE IF NOT EXISTS stocks (
    ts_code VARCHAR(20) PRIMARY KEY,
    symbol VARCHAR(10),
    name VARCHAR(100),
    area VARCHAR(50),
    industry VARCHAR(100),
    market VARCHAR(20),
    list_date DATE,
    is_hs VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建原始价格数据表
CREATE TABLE IF NOT EXISTS stock_prices_raw (
    time TIMESTAMPTZ NOT NULL,
    ts_code VARCHAR(20) NOT NULL,
    open DECIMAL(10,4),
    high DECIMAL(10,4),
    low DECIMAL(10,4),
    close DECIMAL(10,4),
    pre_close DECIMAL(10,4),
    change DECIMAL(10,4),
    pct_chg DECIMAL(8,4),
    vol BIGINT,
    amount DECIMAL(15,2),
    data_source VARCHAR(20) DEFAULT 'tushare',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 转换为 TimescaleDB 超表
SELECT create_hypertable('stock_prices_raw', 'time', if_not_exists => TRUE);

-- 添加空间分区（按股票代码）
SELECT add_dimension('stock_prices_raw', 'ts_code', number_partitions => 4, if_not_exists => TRUE);

-- 启用压缩
ALTER TABLE stock_prices_raw SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'time DESC'
);