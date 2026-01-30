-- 006_monitoring_tables.sql
-- 监控与日志系统数据库表
-- 创建时间: 2026-01-30

-- ============================================
-- 性能指标表
-- ============================================

CREATE TABLE IF NOT EXISTS performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_type VARCHAR(20) NOT NULL,  -- counter, gauge, histogram, timer
    unit VARCHAR(50),
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE performance_metrics IS '性能指标记录表';
COMMENT ON COLUMN performance_metrics.metric_name IS '指标名称';
COMMENT ON COLUMN performance_metrics.metric_value IS '指标值';
COMMENT ON COLUMN performance_metrics.metric_type IS '指标类型';
COMMENT ON COLUMN performance_metrics.tags IS '标签(JSON格式)';
COMMENT ON COLUMN performance_metrics.metadata IS '元数据(JSON格式)';

CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON performance_metrics(metric_name, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON performance_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON performance_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_tags ON performance_metrics USING GIN(tags);

-- ============================================
-- 计时记录表
-- ============================================

CREATE TABLE IF NOT EXISTS timing_records (
    id BIGSERIAL PRIMARY KEY,
    operation VARCHAR(255) NOT NULL,
    duration_ms DOUBLE PRECISION NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    context JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE timing_records IS '操作计时记录表';
COMMENT ON COLUMN timing_records.operation IS '操作名称';
COMMENT ON COLUMN timing_records.duration_ms IS '持续时间(毫秒)';
COMMENT ON COLUMN timing_records.success IS '是否成功';
COMMENT ON COLUMN timing_records.context IS '上下文信息(JSON格式)';

CREATE INDEX IF NOT EXISTS idx_timing_operation_time ON timing_records(operation, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_timing_started_at ON timing_records(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_timing_duration ON timing_records(duration_ms DESC);
CREATE INDEX IF NOT EXISTS idx_timing_slow_queries ON timing_records(duration_ms DESC) WHERE duration_ms > 1000;
CREATE INDEX IF NOT EXISTS idx_timing_success ON timing_records(success);
CREATE INDEX IF NOT EXISTS idx_timing_context ON timing_records USING GIN(context);

-- ============================================
-- 内存使用记录表
-- ============================================

CREATE TABLE IF NOT EXISTS memory_snapshots (
    id BIGSERIAL PRIMARY KEY,
    rss_mb DOUBLE PRECISION NOT NULL,
    vms_mb DOUBLE PRECISION NOT NULL,
    system_memory_percent DOUBLE PRECISION NOT NULL,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE memory_snapshots IS '内存使用快照表';
COMMENT ON COLUMN memory_snapshots.rss_mb IS '实际物理内存(MB)';
COMMENT ON COLUMN memory_snapshots.vms_mb IS '虚拟内存(MB)';
COMMENT ON COLUMN memory_snapshots.system_memory_percent IS '系统内存使用率(%)';

CREATE INDEX IF NOT EXISTS idx_memory_time ON memory_snapshots(snapshot_at DESC);

-- ============================================
-- 数据库查询性能表
-- ============================================

CREATE TABLE IF NOT EXISTS database_query_performance (
    id BIGSERIAL PRIMARY KEY,
    query_hash VARCHAR(64) NOT NULL,
    query_text TEXT NOT NULL,
    query_type VARCHAR(20),  -- SELECT, INSERT, UPDATE, DELETE
    duration_ms DOUBLE PRECISION NOT NULL,
    rows_returned INT,
    is_slow BOOLEAN GENERATED ALWAYS AS (duration_ms > 1000) STORED,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE database_query_performance IS '数据库查询性能表';
COMMENT ON COLUMN database_query_performance.query_hash IS '查询哈希值';
COMMENT ON COLUMN database_query_performance.query_type IS '查询类型';
COMMENT ON COLUMN database_query_performance.is_slow IS '是否为慢查询(自动计算)';

CREATE INDEX IF NOT EXISTS idx_db_query_hash ON database_query_performance(query_hash);
CREATE INDEX IF NOT EXISTS idx_db_query_type ON database_query_performance(query_type);
CREATE INDEX IF NOT EXISTS idx_db_executed_at ON database_query_performance(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_db_slow_queries ON database_query_performance(executed_at DESC) WHERE is_slow = TRUE;
CREATE INDEX IF NOT EXISTS idx_db_duration ON database_query_performance(duration_ms DESC);

-- ============================================
-- 错误事件表 (如果不存在则创建)
-- ============================================

CREATE TABLE IF NOT EXISTS error_events (
    id BIGSERIAL PRIMARY KEY,
    error_hash VARCHAR(64) NOT NULL,
    error_type VARCHAR(255) NOT NULL,
    error_message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL,
    module VARCHAR(255),
    function VARCHAR(255),
    stack_trace TEXT,
    context JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ
);

COMMENT ON TABLE error_events IS '错误事件表';
COMMENT ON COLUMN error_events.error_hash IS '错误哈希值(用于分组相同错误)';
COMMENT ON COLUMN error_events.severity IS '严重程度: CRITICAL, ERROR, WARNING';

CREATE INDEX IF NOT EXISTS idx_error_hash ON error_events(error_hash);
CREATE INDEX IF NOT EXISTS idx_error_occurred_at ON error_events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_severity ON error_events(severity);
CREATE INDEX IF NOT EXISTS idx_error_resolved ON error_events(resolved);
CREATE INDEX IF NOT EXISTS idx_error_type ON error_events(error_type);
CREATE INDEX IF NOT EXISTS idx_error_context ON error_events USING GIN(context);

-- ============================================
-- 错误统计表
-- ============================================

CREATE TABLE IF NOT EXISTS error_statistics (
    id SERIAL PRIMARY KEY,
    error_hash VARCHAR(64) NOT NULL UNIQUE,
    occurrence_count INT NOT NULL DEFAULT 1,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE error_statistics IS '错误统计表';
COMMENT ON COLUMN error_statistics.occurrence_count IS '发生次数';

CREATE INDEX IF NOT EXISTS idx_error_stats_hash ON error_statistics(error_hash);
CREATE INDEX IF NOT EXISTS idx_error_stats_count ON error_statistics(occurrence_count DESC);
CREATE INDEX IF NOT EXISTS idx_error_stats_last_seen ON error_statistics(last_seen DESC);

-- ============================================
-- 使用TimescaleDB超表优化时序数据
-- ============================================

-- 检查TimescaleDB扩展是否可用
DO $$
BEGIN
    -- 尝试创建超表
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
    ) THEN
        -- 性能指标超表
        PERFORM create_hypertable(
            'performance_metrics',
            'recorded_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );

        -- 计时记录超表
        PERFORM create_hypertable(
            'timing_records',
            'started_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );

        -- 内存快照超表
        PERFORM create_hypertable(
            'memory_snapshots',
            'snapshot_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );

        -- 数据库查询性能超表
        PERFORM create_hypertable(
            'database_query_performance',
            'executed_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        );

        -- 错误事件超表
        PERFORM create_hypertable(
            'error_events',
            'occurred_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        );

        RAISE NOTICE 'TimescaleDB hypertables created successfully';
    ELSE
        RAISE NOTICE 'TimescaleDB extension not available, using regular tables';
    END IF;
END
$$;

-- ============================================
-- 数据保留策略 (如果TimescaleDB可用)
-- ============================================

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
    ) THEN
        -- 性能指标保留30天
        PERFORM add_retention_policy(
            'performance_metrics',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        -- 计时记录保留30天
        PERFORM add_retention_policy(
            'timing_records',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        -- 内存快照保留7天
        PERFORM add_retention_policy(
            'memory_snapshots',
            INTERVAL '7 days',
            if_not_exists => TRUE
        );

        -- 数据库查询性能保留30天
        PERFORM add_retention_policy(
            'database_query_performance',
            INTERVAL '30 days',
            if_not_exists => TRUE
        );

        -- 错误事件保留90天
        PERFORM add_retention_policy(
            'error_events',
            INTERVAL '90 days',
            if_not_exists => TRUE
        );

        RAISE NOTICE 'Retention policies configured successfully';
    END IF;
END
$$;

-- ============================================
-- 创建有用的视图
-- ============================================

-- 慢查询视图
CREATE OR REPLACE VIEW slow_queries_summary AS
SELECT
    query_type,
    COUNT(*) as slow_query_count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    MIN(executed_at) as first_occurrence,
    MAX(executed_at) as last_occurrence
FROM database_query_performance
WHERE is_slow = TRUE
    AND executed_at >= NOW() - INTERVAL '24 hours'
GROUP BY query_type
ORDER BY slow_query_count DESC;

COMMENT ON VIEW slow_queries_summary IS '过去24小时慢查询汇总视图';

-- 错误汇总视图
CREATE OR REPLACE VIEW error_summary AS
SELECT
    error_type,
    severity,
    COUNT(*) as occurrence_count,
    MIN(occurred_at) as first_seen,
    MAX(occurred_at) as last_seen,
    COUNT(*) FILTER (WHERE resolved = FALSE) as unresolved_count
FROM error_events
WHERE occurred_at >= NOW() - INTERVAL '24 hours'
GROUP BY error_type, severity
ORDER BY occurrence_count DESC;

COMMENT ON VIEW error_summary IS '过去24小时错误汇总视图';

-- 性能指标汇总视图
CREATE OR REPLACE VIEW performance_metrics_summary AS
SELECT
    metric_name,
    metric_type,
    COUNT(*) as record_count,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    MIN(recorded_at) as first_recorded,
    MAX(recorded_at) as last_recorded
FROM performance_metrics
WHERE recorded_at >= NOW() - INTERVAL '1 hour'
GROUP BY metric_name, metric_type
ORDER BY metric_name;

COMMENT ON VIEW performance_metrics_summary IS '过去1小时性能指标汇总视图';

-- ============================================
-- 创建清理函数
-- ============================================

CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data(days_to_keep INTEGER DEFAULT 30)
RETURNS TABLE(
    table_name TEXT,
    deleted_rows BIGINT
) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    rows_deleted BIGINT;
BEGIN
    cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

    -- 清理性能指标
    DELETE FROM performance_metrics WHERE recorded_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'performance_metrics';
    deleted_rows := rows_deleted;
    RETURN NEXT;

    -- 清理计时记录
    DELETE FROM timing_records WHERE started_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'timing_records';
    deleted_rows := rows_deleted;
    RETURN NEXT;

    -- 清理内存快照
    DELETE FROM memory_snapshots WHERE snapshot_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'memory_snapshots';
    deleted_rows := rows_deleted;
    RETURN NEXT;

    -- 清理数据库查询性能
    DELETE FROM database_query_performance WHERE executed_at < cutoff_date;
    GET DIAGNOSTICS rows_deleted = ROW_COUNT;
    table_name := 'database_query_performance';
    deleted_rows := rows_deleted;
    RETURN NEXT;

    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_monitoring_data IS '清理指定天数之前的监控数据';

-- ============================================
-- 完成信息
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Monitoring tables migration completed!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Created tables:';
    RAISE NOTICE '  - performance_metrics';
    RAISE NOTICE '  - timing_records';
    RAISE NOTICE '  - memory_snapshots';
    RAISE NOTICE '  - database_query_performance';
    RAISE NOTICE '  - error_events';
    RAISE NOTICE '  - error_statistics';
    RAISE NOTICE '';
    RAISE NOTICE 'Created views:';
    RAISE NOTICE '  - slow_queries_summary';
    RAISE NOTICE '  - error_summary';
    RAISE NOTICE '  - performance_metrics_summary';
    RAISE NOTICE '';
    RAISE NOTICE 'Created functions:';
    RAISE NOTICE '  - cleanup_old_monitoring_data(days_to_keep)';
    RAISE NOTICE '========================================';
END
$$;
