-- =====================================================
-- TimescaleDB 性能优化配置
-- 包括数据压缩策略、索引优化、分区管理等
-- =====================================================

-- 1. 数据压缩策略配置
-- =====================================================

-- 启用压缩（如果尚未启用）
ALTER TABLE daily_basic SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date DESC'
);

ALTER TABLE moneyflow SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date DESC'
);

ALTER TABLE hk_hold SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'code,exchange',
    timescaledb.compress_orderby = 'trade_date DESC'
);

ALTER TABLE margin_detail SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date DESC'
);

ALTER TABLE adj_factor SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date DESC'
);

ALTER TABLE stk_limit SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date DESC'
);

-- 添加自动压缩策略（90天后自动压缩）
SELECT add_compression_policy('daily_basic', INTERVAL '90 days', if_not_exists => true);
SELECT add_compression_policy('moneyflow', INTERVAL '90 days', if_not_exists => true);
SELECT add_compression_policy('hk_hold', INTERVAL '90 days', if_not_exists => true);
SELECT add_compression_policy('margin_detail', INTERVAL '90 days', if_not_exists => true);
SELECT add_compression_policy('adj_factor', INTERVAL '180 days', if_not_exists => true);
SELECT add_compression_policy('stk_limit', INTERVAL '90 days', if_not_exists => true);

-- 对于大宗交易，30天后压缩
SELECT add_compression_policy('block_trade', INTERVAL '30 days', if_not_exists => true);

-- 2. 创建优化索引
-- =====================================================

-- 每日指标索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_daily_basic_date_code
ON daily_basic(trade_date DESC, ts_code);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_daily_basic_turnover
ON daily_basic(turnover_rate DESC)
WHERE turnover_rate > 10;  -- 高换手率

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_daily_basic_pe
ON daily_basic(pe)
WHERE pe > 0 AND pe < 100;  -- 合理PE区间

-- 资金流向索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_moneyflow_date_code
ON moneyflow(trade_date DESC, ts_code);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_moneyflow_net_amount
ON moneyflow(net_mf_amount DESC)
WHERE net_mf_amount != 0;  -- 净流入不为0

-- 北向资金索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hk_hold_date_code
ON hk_hold(trade_date DESC, code, exchange);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_hk_hold_ratio
ON hk_hold(ratio DESC)
WHERE ratio > 5;  -- 持股占比大于5%

-- 融资融券索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_margin_detail_date_code
ON margin_detail(trade_date DESC, ts_code);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_margin_detail_rzrqye
ON margin_detail(rzrqye DESC);

-- 涨跌停价格索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_stk_limit_date_code
ON stk_limit(trade_date DESC, ts_code);

-- 大宗交易索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_block_trade_date_code
ON block_trade(trade_date DESC, ts_code);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_block_trade_amount
ON block_trade(amount DESC);

-- 3. 创建连续聚合视图（物化视图）
-- =====================================================

-- 每日市场概览
CREATE MATERIALIZED VIEW IF NOT EXISTS market_daily_overview
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', trade_date) AS day,
    COUNT(DISTINCT ts_code) AS stock_count,
    AVG(turnover_rate) AS avg_turnover_rate,
    AVG(pe) AS avg_pe,
    AVG(pb) AS avg_pb,
    SUM(total_mv) AS total_market_value,
    MAX(trade_date) AS latest_date
FROM daily_basic
WHERE trade_date >= NOW() - INTERVAL '1 year'
GROUP BY day
WITH NO DATA;

-- 刷新策略：每天刷新一次
SELECT add_continuous_aggregate_policy('market_daily_overview',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => true);

-- 资金流向汇总
CREATE MATERIALIZED VIEW IF NOT EXISTS moneyflow_daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', trade_date) AS day,
    ts_code,
    SUM(net_mf_amount) AS total_net_inflow,
    SUM(buy_lg_amount + buy_elg_amount) AS total_large_buy,
    SUM(sell_lg_amount + sell_elg_amount) AS total_large_sell,
    AVG(net_mf_amount) AS avg_net_inflow
FROM moneyflow
WHERE trade_date >= NOW() - INTERVAL '6 months'
GROUP BY day, ts_code
WITH NO DATA;

-- 刷新策略
SELECT add_continuous_aggregate_policy('moneyflow_daily_summary',
    start_offset => INTERVAL '1 week',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => true);

-- 北向资金趋势
CREATE MATERIALIZED VIEW IF NOT EXISTS hk_hold_trend
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', trade_date) AS day,
    exchange,
    COUNT(DISTINCT code) AS stock_count,
    SUM(vol) AS total_volume,
    AVG(ratio) AS avg_ratio
FROM hk_hold
WHERE trade_date >= NOW() - INTERVAL '3 months'
GROUP BY day, exchange
WITH NO DATA;

-- 刷新策略
SELECT add_continuous_aggregate_policy('hk_hold_trend',
    start_offset => INTERVAL '1 week',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => true);

-- 4. 数据保留策略
-- =====================================================

-- 设置数据保留策略（保留2年数据）
SELECT add_retention_policy('daily_basic', INTERVAL '2 years', if_not_exists => true);
SELECT add_retention_policy('moneyflow', INTERVAL '1 year', if_not_exists => true);
SELECT add_retention_policy('hk_hold', INTERVAL '1 year', if_not_exists => true);
SELECT add_retention_policy('margin_detail', INTERVAL '2 years', if_not_exists => true);
SELECT add_retention_policy('block_trade', INTERVAL '6 months', if_not_exists => true);

-- 5. 分区管理优化
-- =====================================================

-- 调整chunk时间间隔（每个chunk包含1个月数据）
SELECT set_chunk_time_interval('daily_basic', INTERVAL '1 month');
SELECT set_chunk_time_interval('moneyflow', INTERVAL '1 month');
SELECT set_chunk_time_interval('hk_hold', INTERVAL '1 month');
SELECT set_chunk_time_interval('margin_detail', INTERVAL '1 month');
SELECT set_chunk_time_interval('stk_limit', INTERVAL '1 month');

-- 6. 统计信息更新
-- =====================================================

-- 更新表统计信息
ANALYZE daily_basic;
ANALYZE moneyflow;
ANALYZE hk_hold;
ANALYZE margin_detail;
ANALYZE adj_factor;
ANALYZE stk_limit;
ANALYZE block_trade;

-- 7. 创建常用查询函数
-- =====================================================

-- 获取股票最新指标
CREATE OR REPLACE FUNCTION get_latest_daily_basic(p_ts_code VARCHAR)
RETURNS TABLE (
    ts_code VARCHAR,
    trade_date DATE,
    turnover_rate DECIMAL,
    pe DECIMAL,
    pb DECIMAL,
    total_mv DECIMAL,
    circ_mv DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        db.ts_code,
        db.trade_date,
        db.turnover_rate,
        db.pe,
        db.pb,
        db.total_mv,
        db.circ_mv
    FROM daily_basic db
    WHERE db.ts_code = p_ts_code
    ORDER BY db.trade_date DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 获取资金流向排行
CREATE OR REPLACE FUNCTION get_moneyflow_top(
    p_trade_date DATE,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    ts_code VARCHAR,
    net_mf_amount DECIMAL,
    buy_lg_amount DECIMAL,
    sell_lg_amount DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        mf.ts_code,
        mf.net_mf_amount,
        mf.buy_lg_amount,
        mf.sell_lg_amount
    FROM moneyflow mf
    WHERE mf.trade_date = p_trade_date
    ORDER BY mf.net_mf_amount DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- 8. 性能监控视图
-- =====================================================

-- 创建压缩状态监控视图
CREATE OR REPLACE VIEW compression_status AS
SELECT
    hypertable_name,
    chunk_name,
    compression_status,
    uncompressed_heap_size,
    compressed_heap_size,
    CASE
        WHEN uncompressed_heap_size > 0
        THEN (1.0 - compressed_heap_size::float / uncompressed_heap_size::float) * 100
        ELSE 0
    END AS compression_ratio
FROM timescaledb_information.chunks
WHERE compression_status IS NOT NULL
ORDER BY hypertable_name, chunk_name;

-- 查询性能统计视图
CREATE OR REPLACE VIEW query_performance AS
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time,
    stddev_time
FROM pg_stat_statements
WHERE query LIKE '%daily_basic%'
   OR query LIKE '%moneyflow%'
   OR query LIKE '%hk_hold%'
   OR query LIKE '%margin_detail%'
ORDER BY total_time DESC
LIMIT 50;

-- 9. 维护任务
-- =====================================================

-- 创建定期维护函数
CREATE OR REPLACE FUNCTION perform_maintenance()
RETURNS void AS $$
BEGIN
    -- 更新统计信息
    ANALYZE daily_basic;
    ANALYZE moneyflow;
    ANALYZE hk_hold;
    ANALYZE margin_detail;

    -- 重新组织索引
    REINDEX TABLE CONCURRENTLY daily_basic;
    REINDEX TABLE CONCURRENTLY moneyflow;

    -- 清理死元组
    VACUUM (ANALYZE) daily_basic;
    VACUUM (ANALYZE) moneyflow;

    RAISE NOTICE '维护任务完成';
END;
$$ LANGUAGE plpgsql;

-- 添加定期维护任务（每周日凌晨2点执行）
SELECT cron.schedule(
    'weekly_maintenance',
    '0 2 * * 0',
    'SELECT perform_maintenance();'
);

-- 10. 查询优化提示
-- =====================================================

-- 为常用查询启用并行查询
ALTER TABLE daily_basic SET (parallel_workers = 4);
ALTER TABLE moneyflow SET (parallel_workers = 4);

-- 调整工作内存（提高排序和哈希操作性能）
-- 注意：这些设置应该在postgresql.conf中配置
-- SET work_mem = '256MB';
-- SET maintenance_work_mem = '512MB';
-- SET effective_cache_size = '4GB';

-- =====================================================
-- 优化完成
-- 执行此脚本后，数据库性能将得到显著提升
-- =====================================================

-- 查看优化效果
SELECT
    'daily_basic' as table_name,
    pg_size_pretty(pg_total_relation_size('daily_basic')) as size
UNION ALL
SELECT
    'moneyflow',
    pg_size_pretty(pg_total_relation_size('moneyflow'))
UNION ALL
SELECT
    'hk_hold',
    pg_size_pretty(pg_total_relation_size('hk_hold'))
UNION ALL
SELECT
    'margin_detail',
    pg_size_pretty(pg_total_relation_size('margin_detail'))
ORDER BY table_name;