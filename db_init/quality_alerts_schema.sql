-- =====================================================
-- 数据质量告警配置表
-- 创建时间：2024-03
-- 说明：配置数据质量监控告警规则和记录
-- =====================================================

-- 创建告警配置表
CREATE TABLE IF NOT EXISTS quality_alert_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    data_source VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- completeness, accuracy, timeliness, record_count
    threshold_type VARCHAR(20) NOT NULL, -- min, max, range
    threshold_value DECIMAL(10,4) NOT NULL,
    threshold_max DECIMAL(10,4), -- 用于range类型
    severity VARCHAR(20) NOT NULL DEFAULT 'medium', -- low, medium, high
    enabled BOOLEAN DEFAULT true,
    notification_channels JSONB, -- 通知渠道配置
    cooldown_minutes INT DEFAULT 60, -- 告警冷却时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建告警记录表
CREATE TABLE IF NOT EXISTS quality_alerts (
    id SERIAL PRIMARY KEY,
    config_id INT REFERENCES quality_alert_configs(id) ON DELETE CASCADE,
    data_source VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,4),
    threshold_value DECIMAL(10,4),
    severity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'active', -- active, acknowledged, resolved, expired
    message TEXT,
    details JSONB,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_quality_alert_configs_data_source ON quality_alert_configs(data_source);
CREATE INDEX idx_quality_alert_configs_enabled ON quality_alert_configs(enabled);
CREATE INDEX idx_quality_alerts_status ON quality_alerts(status);
CREATE INDEX idx_quality_alerts_created_at ON quality_alerts(created_at DESC);
CREATE INDEX idx_quality_alerts_config_id ON quality_alerts(config_id);

-- 插入默认告警配置
INSERT INTO quality_alert_configs (name, description, data_source, metric_type, threshold_type, threshold_value, severity) VALUES
-- 完整性告警
('daily_basic_completeness_low', '每日指标完整性过低', 'daily_basic', 'completeness', 'min', 95.0, 'medium'),
('moneyflow_completeness_critical', '资金流向数据完整性严重不足', 'moneyflow', 'completeness', 'min', 90.0, 'high'),
('hk_hold_completeness_warning', '北向资金数据完整性警告', 'hk_hold', 'completeness', 'min', 98.0, 'low'),

-- 准确性告警
('daily_basic_accuracy_low', '每日指标准确性过低', 'daily_basic', 'accuracy', 'min', 99.0, 'medium'),
('margin_detail_accuracy_critical', '融资融券数据准确性问题', 'margin_detail', 'accuracy', 'min', 98.0, 'high'),

-- 及时性告警
('daily_basic_timeliness_warning', '每日指标数据延迟', 'daily_basic', 'timeliness', 'min', 95.0, 'medium'),
('stk_limit_timeliness_critical', '涨跌停数据严重延迟', 'stk_limit', 'timeliness', 'min', 99.0, 'high'),

-- 记录数告警
('moneyflow_record_too_low', '资金流向记录数异常偏低', 'moneyflow', 'record_count', 'min', 100, 'high'),
('daily_basic_record_spike', '每日指标记录数异常', 'daily_basic', 'record_count', 'range', 3000, 'medium')
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    threshold_value = EXCLUDED.threshold_value,
    severity = EXCLUDED.severity,
    updated_at = CURRENT_TIMESTAMP;

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_quality_alert_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_quality_alert_configs_timestamp
    BEFORE UPDATE ON quality_alert_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_quality_alert_timestamp();

CREATE TRIGGER update_quality_alerts_timestamp
    BEFORE UPDATE ON quality_alerts
    FOR EACH ROW
    EXECUTE FUNCTION update_quality_alert_timestamp();

-- 输出创建完成信息
DO $$
BEGIN
    RAISE NOTICE '质量告警配置表已创建';
    RAISE NOTICE '已插入9个默认告警规则';
END $$;