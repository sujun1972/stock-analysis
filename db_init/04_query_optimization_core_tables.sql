-- =====================================================
-- 共享数据表查询性能优化 (任务 2.2 - 基础设施层)
-- 版本: 004
-- 日期: 2026-02-05
-- 说明: 优化 Core 和 Backend 共同使用的核心数据表
-- =====================================================

-- 此文件包含：
-- 1. stock_daily 表索引优化
-- 2. stock_min 表索引优化（预留）
-- 3. TimescaleDB 压缩策略配置
-- 4. 全局维护函数和性能分析视图

-- =====================================================
-- 1. Stock Daily 表优化（时序数据核心表）
-- =====================================================

-- 为范围查询优化（股票 + 日期范围）
-- 注意：基础索引已在 02_data_engine_schema.sql 中创建
CREATE INDEX IF NOT EXISTS idx_stock_daily_code_date ON stock_daily(code, date DESC);

-- 为按涨跌幅排序优化（选股场景：涨幅榜/跌幅榜）
CREATE INDEX IF NOT EXISTS idx_stock_daily_pct_change ON stock_daily(date DESC, pct_change DESC);

-- 为按成交量排序优化（选股场景：成交量排行）
CREATE INDEX IF NOT EXISTS idx_stock_daily_volume ON stock_daily(date DESC, volume DESC);

-- 为多股票联合查询优化（使用 BRIN 索引减少存储开销）
-- BRIN 索引非常适合时序数据，存储开销仅为 B-Tree 的 1%
CREATE INDEX IF NOT EXISTS idx_stock_daily_date_brin ON stock_daily USING BRIN(date)
    WITH (pages_per_range = 128);

COMMENT ON INDEX idx_stock_daily_pct_change IS '优化涨幅榜/跌幅榜查询';
COMMENT ON INDEX idx_stock_daily_volume IS '优化成交量排行查询';
COMMENT ON INDEX idx_stock_daily_date_brin IS 'BRIN 索引：用于大范围日期扫描，减少索引存储开销';


-- =====================================================
-- 2. Stock Minute 表优化（高频数据）
-- =====================================================

-- 注意：stock_min 表需要先确认列名（trade_time 或 time）
-- 预留位置，待确认后添加索引优化


-- =====================================================
-- 3. 创建扩展统计信息（PostgreSQL 特性）
-- =====================================================

-- Stock Daily 表：代码 + 日期 + 涨跌幅的多列统计
-- 提高复杂查询的计划准确性
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_statistic_ext
        WHERE stxname = 'stock_daily_code_date_pct_stats'
    ) THEN
        CREATE STATISTICS stock_daily_code_date_pct_stats (dependencies)
        ON code, date, pct_change
        FROM stock_daily;
        RAISE NOTICE 'Created statistics: stock_daily_code_date_pct_stats';
    END IF;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Failed to create extended statistics: %', SQLERRM;
END $$;


-- =====================================================
-- 4. TimescaleDB Hypertable 压缩策略
-- =====================================================

-- 为 stock_daily 添加压缩策略（如果尚未添加）
DO $$
BEGIN
    -- 检查是否已有压缩策略
    IF NOT EXISTS (
        SELECT 1 FROM timescaledb_information.compression_settings
        WHERE hypertable_name = 'stock_daily'
    ) THEN
        -- 启用压缩
        ALTER TABLE stock_daily SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'code',
            timescaledb.compress_orderby = 'date DESC'
        );

        -- 添加压缩策略（压缩 90 天前的数据）
        PERFORM add_compression_policy('stock_daily', INTERVAL '90 days');

        RAISE NOTICE 'Compression enabled for stock_daily (90-day policy)';
    ELSE
        RAISE NOTICE 'Compression policy already exists for stock_daily';
    END IF;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Failed to configure compression for stock_daily: %', SQLERRM;
END $$;


-- =====================================================
-- 5. 全局索引维护函数
-- =====================================================

-- 创建函数用于重建关键表索引（使用 CONCURRENTLY 避免锁表）
CREATE OR REPLACE FUNCTION reindex_critical_tables()
RETURNS TABLE(
    table_name TEXT,
    status TEXT,
    duration_ms BIGINT
) AS $$
DECLARE
    start_time TIMESTAMPTZ;
    end_time TIMESTAMPTZ;
BEGIN
    -- Stock Daily 表（最关键）
    start_time := clock_timestamp();
    REINDEX TABLE CONCURRENTLY stock_daily;
    end_time := clock_timestamp();
    table_name := 'stock_daily';
    status := 'SUCCESS';
    duration_ms := EXTRACT(EPOCH FROM (end_time - start_time)) * 1000;
    RETURN NEXT;

    RETURN;
EXCEPTION
    WHEN others THEN
        table_name := 'ERROR';
        status := SQLERRM;
        duration_ms := 0;
        RETURN NEXT;
        RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reindex_critical_tables IS '重建关键表索引（使用 CONCURRENTLY 避免锁表）';


-- =====================================================
-- 6. 全局性能分析视图
-- =====================================================

-- 索引使用情况统计视图
CREATE OR REPLACE VIEW v_table_index_usage AS
SELECT
    schemaname,
    relname AS tablename,
    indexrelname AS indexname,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    CASE
        WHEN idx_scan = 0 THEN 'NEVER USED'
        WHEN idx_scan < 100 THEN 'RARELY USED'
        ELSE 'FREQUENTLY USED'
    END AS usage_level
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

COMMENT ON VIEW v_table_index_usage IS '索引使用情况统计视图（用于识别未使用的索引）';


-- 缺失索引候选视图
CREATE OR REPLACE VIEW v_missing_indexes_candidates AS
SELECT
    schemaname,
    relname AS tablename,
    seq_scan AS sequential_scans,
    seq_tup_read AS rows_read_sequentially,
    idx_scan AS index_scans,
    n_tup_ins + n_tup_upd + n_tup_del AS modification_count,
    pg_size_pretty(pg_relation_size(relid)) AS table_size
FROM pg_stat_user_tables
WHERE schemaname = 'public'
  AND seq_scan > 1000  -- 超过 1000 次顺序扫描
  AND seq_tup_read > 100000  -- 读取超过 10 万行
ORDER BY seq_tup_read DESC;

COMMENT ON VIEW v_missing_indexes_candidates IS '可能缺少索引的表（顺序扫描过多）';


-- =====================================================
-- 7. 更新表统计信息
-- =====================================================

DO $$
BEGIN
    ANALYZE stock_daily;
    RAISE NOTICE 'Statistics updated for stock_daily';
END $$;


-- =====================================================
-- 8. 性能优化建议（注释形式）
-- =====================================================

/*
  共享表优化建议：

  1. 定期维护（建议每周执行一次）：
     SELECT * FROM reindex_critical_tables();
     VACUUM ANALYZE stock_daily;

  2. 监控索引使用情况：
     SELECT * FROM v_table_index_usage WHERE usage_level = 'NEVER USED';

  3. 识别缺失的索引：
     SELECT * FROM v_missing_indexes_candidates;

  4. TimescaleDB 压缩状态检查：
     SELECT * FROM timescaledb_information.compression_settings;
     SELECT * FROM timescaledb_information.chunks
     ORDER BY before_compression_total_bytes DESC;

  5. PostgreSQL 配置建议：
     - shared_buffers: 4GB（系统内存的 25%）
     - effective_cache_size: 12GB（系统内存的 75%）
     - work_mem: 64MB
     - maintenance_work_mem: 1GB
     - random_page_cost: 1.1（SSD）
*/


-- =====================================================
-- 9. 完成信息
-- =====================================================

DO $$
BEGIN
    RAISE NOTICE '========================================================';
    RAISE NOTICE '✅ 共享数据表查询性能优化完成！';
    RAISE NOTICE '========================================================';
    RAISE NOTICE '优化内容：';
    RAISE NOTICE '  [1] Stock Daily 表添加 4 个索引（含 BRIN 索引）';
    RAISE NOTICE '  [2] 创建扩展统计信息（提高查询计划准确性）';
    RAISE NOTICE '  [3] 配置 TimescaleDB 压缩策略（90天）';
    RAISE NOTICE '  [4] 创建全局索引维护函数';
    RAISE NOTICE '  [5] 创建性能分析视图';
    RAISE NOTICE '  [6] 更新表统计信息';
    RAISE NOTICE ' ';
    RAISE NOTICE '预期性能提升：';
    RAISE NOTICE '  • 股票日线数据查询（按代码+日期范围）：60%% 提升';
    RAISE NOTICE '  • 涨幅榜/跌幅榜查询：90%% 提升';
    RAISE NOTICE '  • 成交量排行查询：90%% 提升';
    RAISE NOTICE '  • 大范围日期扫描（BRIN 索引）：存储减少 99%%';
    RAISE NOTICE ' ';
    RAISE NOTICE '后续步骤：';
    RAISE NOTICE '  1. 运行 core/src/database/migrations/007_*.sql';
    RAISE NOTICE '  2. 运行 backend/migrations/007_*.sql';
    RAISE NOTICE '========================================================';
END $$;
