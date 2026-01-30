-- Migration: 005_data_source_health
-- Description: 创建数据源健康监控表
-- Date: 2026-01-30

-- ============================================================
-- 数据源健康状态表
-- ============================================================
CREATE TABLE IF NOT EXISTS data_source_health (
    provider_name VARCHAR(50) PRIMARY KEY,
    health_score FLOAT DEFAULT 100.0,         -- 健康分数 (0-100)
    total_requests INTEGER DEFAULT 0,         -- 总请求数
    success_count INTEGER DEFAULT 0,          -- 成功次数
    failure_count INTEGER DEFAULT 0,          -- 失败次数
    consecutive_failures INTEGER DEFAULT 0,   -- 连续失败次数
    last_success_at TIMESTAMP,                -- 最后成功时间
    last_failure_at TIMESTAMP,                -- 最后失败时间
    last_error_message TEXT,                  -- 最后错误信息
    is_available BOOLEAN DEFAULT TRUE,        -- 是否可用
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_data_source_health_available ON data_source_health(is_available);
CREATE INDEX IF NOT EXISTS idx_data_source_health_score ON data_source_health(health_score);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_data_source_health_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_data_source_health_updated_at
BEFORE UPDATE ON data_source_health
FOR EACH ROW
EXECUTE FUNCTION update_data_source_health_updated_at();

-- ============================================================
-- 数据源健康事件日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS data_source_health_events (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,          -- 事件类型：'success', 'failure', 'degraded', 'recovered'
    health_score FLOAT,                        -- 事件时的健康分数
    message TEXT,                              -- 事件消息
    details JSONB,                             -- 详细信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_data_source_health_events_provider ON data_source_health_events(provider_name);
CREATE INDEX IF NOT EXISTS idx_data_source_health_events_type ON data_source_health_events(event_type);
CREATE INDEX IF NOT EXISTS idx_data_source_health_events_created_at ON data_source_health_events(created_at);

-- ============================================================
-- 初始化数据源
-- ============================================================
INSERT INTO data_source_health (provider_name, health_score, is_available)
VALUES
    ('akshare', 100.0, TRUE),
    ('tushare', 100.0, TRUE)
ON CONFLICT (provider_name) DO NOTHING;

-- ============================================================
-- 注释
-- ============================================================
COMMENT ON TABLE data_source_health IS '数据源健康状态表';
COMMENT ON COLUMN data_source_health.health_score IS '健康分数，0-100，越高越健康';
COMMENT ON COLUMN data_source_health.consecutive_failures IS '连续失败次数，用于判断是否降级';
COMMENT ON COLUMN data_source_health.is_available IS '是否可用，false时不再使用该数据源';

COMMENT ON TABLE data_source_health_events IS '数据源健康事件日志表';
COMMENT ON COLUMN data_source_health_events.event_type IS '事件类型：success/failure/degraded/recovered';
