-- =====================================================
-- 通知系统数据库表
-- 创建日期: 2026-03-15
-- 说明: 支持多渠道通知推送（Email、Telegram、站内消息）
-- =====================================================

-- =====================================================
-- 1. 通知渠道配置表
-- 用途: 管理员在 Admin 后台配置 SMTP、Telegram Bot 等渠道参数
-- =====================================================
CREATE TABLE IF NOT EXISTS notification_channel_configs (
    id SERIAL PRIMARY KEY,

    -- 渠道标识
    channel_type VARCHAR(20) NOT NULL UNIQUE,  -- 'email', 'telegram'
    channel_name VARCHAR(100) NOT NULL,        -- '邮件通知', 'Telegram Bot'

    -- 启用状态
    is_enabled BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,          -- 是否为默认渠道
    priority INTEGER DEFAULT 10,               -- 优先级（数字越小优先级越高）

    -- 配置参数（JSON 格式，根据渠道类型不同）
    config JSONB NOT NULL DEFAULT '{}',
    -- Email 示例:
    -- {
    --   "smtp_host": "smtp.gmail.com",
    --   "smtp_port": 587,
    --   "smtp_username": "noreply@example.com",
    --   "smtp_password": "********",  -- 加密存储
    --   "smtp_use_tls": true,
    --   "from_email": "noreply@example.com",
    --   "from_name": "股票分析系统"
    -- }
    -- Telegram 示例:
    -- {
    --   "bot_token": "1234567890:ABCDEF********",  -- 加密存储
    --   "parse_mode": "Markdown",
    --   "timeout": 30
    -- }

    -- 描述信息
    description TEXT,

    -- 测试状态
    last_test_at TIMESTAMPTZ,                  -- 最后测试时间
    last_test_status VARCHAR(20),              -- 'success', 'failed'
    last_test_message TEXT,                    -- 测试结果消息

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_channel_configs_type ON notification_channel_configs(channel_type);
CREATE INDEX IF NOT EXISTS idx_notification_channel_configs_enabled ON notification_channel_configs(is_enabled);

COMMENT ON TABLE notification_channel_configs IS '通知渠道配置表（管理员配置 SMTP、Telegram Bot 等）';
COMMENT ON COLUMN notification_channel_configs.channel_type IS '渠道类型：email, telegram';
COMMENT ON COLUMN notification_channel_configs.config IS 'JSONB 配置参数（敏感信息加密存储）';

-- 初始化默认配置
INSERT INTO notification_channel_configs (channel_type, channel_name, is_enabled, config, description)
VALUES
('email', '邮件通知', false, '{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_use_tls": true,
    "from_email": "noreply@example.com",
    "from_name": "股票分析系统"
}'::jsonb, 'SMTP 邮件推送服务'),
('telegram', 'Telegram Bot', false, '{
    "bot_token": "",
    "parse_mode": "Markdown",
    "timeout": 30
}'::jsonb, 'Telegram Bot 消息推送')
ON CONFLICT (channel_type) DO NOTHING;


-- =====================================================
-- 2. 用户通知配置表
-- 用途: 用户个性化订阅配置（订阅内容、接收渠道、内容格式）
-- =====================================================
CREATE TABLE IF NOT EXISTS user_notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 通知渠道启用状态
    email_enabled BOOLEAN DEFAULT false,
    telegram_enabled BOOLEAN DEFAULT false,
    in_app_enabled BOOLEAN DEFAULT true,           -- 站内消息默认开启

    -- 联系方式
    email_address VARCHAR(255),
    telegram_chat_id VARCHAR(100),                  -- 用户的 Telegram Chat ID
    telegram_username VARCHAR(100),

    -- 报告订阅偏好
    subscribe_sentiment_report BOOLEAN DEFAULT false,    -- 盘后情绪报告
    subscribe_premarket_report BOOLEAN DEFAULT false,    -- 盘前碰撞报告
    subscribe_backtest_report BOOLEAN DEFAULT true,      -- 回测完成通知
    subscribe_strategy_alert BOOLEAN DEFAULT true,       -- 策略审核通知

    -- 发送时间偏好
    sentiment_report_time TIME DEFAULT '18:30',          -- 盘后报告发送时间
    premarket_report_time TIME DEFAULT '08:00',          -- 盘前报告发送时间

    -- 报告内容偏好
    report_format VARCHAR(20) DEFAULT 'full',            -- 'full'=完整报告, 'summary'=摘要, 'action_only'=仅行动指令

    -- 频率控制
    max_daily_notifications INTEGER DEFAULT 10,          -- 每日最大通知数

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id),
    CONSTRAINT valid_report_format CHECK (report_format IN ('full', 'summary', 'action_only'))
);

CREATE INDEX IF NOT EXISTS idx_user_notification_settings_user_id ON user_notification_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notification_settings_sentiment ON user_notification_settings(subscribe_sentiment_report) WHERE subscribe_sentiment_report = true;
CREATE INDEX IF NOT EXISTS idx_user_notification_settings_premarket ON user_notification_settings(subscribe_premarket_report) WHERE subscribe_premarket_report = true;

COMMENT ON TABLE user_notification_settings IS '用户通知配置表（订阅偏好、接收渠道、内容格式）';
COMMENT ON COLUMN user_notification_settings.report_format IS '报告内容格式：full=完整报告, summary=摘要, action_only=仅行动指令';

-- 新用户自动创建默认配置（触发器）
CREATE OR REPLACE FUNCTION create_default_notification_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_notification_settings (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_create_default_notification_settings ON users;
CREATE TRIGGER trigger_create_default_notification_settings
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_default_notification_settings();


-- =====================================================
-- 3. 通知发送记录表
-- 用途: 追踪每条通知的发送状态和历史（支持时序分区）
-- =====================================================
CREATE TABLE IF NOT EXISTS notification_logs (
    id SERIAL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 通知内容
    notification_type VARCHAR(50) NOT NULL,              -- 'sentiment_report', 'premarket_report', 'backtest_result'
    content_type VARCHAR(20) NOT NULL,                   -- 'full', 'summary', 'action_only'
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,

    -- 发送渠道
    channel VARCHAR(20) NOT NULL,                        -- 'email', 'telegram', 'in_app'

    -- 发送状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending',       -- 'pending', 'sent', 'failed', 'skipped'
    sent_at TIMESTAMPTZ,
    failed_reason TEXT,
    retry_count INTEGER DEFAULT 0,

    -- 关联数据
    business_date DATE,                                   -- 关联的交易日
    reference_id VARCHAR(100),                            -- 关联的业务ID (如回测ID)

    -- Celery 任务ID
    task_id VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_channel CHECK (channel IN ('email', 'telegram', 'in_app')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'sent', 'failed', 'skipped'))
);

-- 索引（在转换为 hypertable 前创建）
CREATE INDEX IF NOT EXISTS idx_notification_logs_user_id ON notification_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_status ON notification_logs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_business_date ON notification_logs(business_date, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notification_logs_type ON notification_logs(notification_type, created_at DESC);

COMMENT ON TABLE notification_logs IS '通知发送记录表（时序分区表）';
COMMENT ON COLUMN notification_logs.status IS '发送状态：pending=待发送, sent=已发送, failed=失败, skipped=跳过';

-- 转换为 TimescaleDB Hypertable（按月分区）
SELECT create_hypertable('notification_logs', 'created_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- 自动清理 6 个月前的日志（保留策略）
SELECT add_retention_policy('notification_logs', INTERVAL '6 months', if_not_exists => TRUE);


-- =====================================================
-- 4. 站内消息表
-- 用途: 存储站内消息（用户前端的通知中心，支持时序分区）
-- =====================================================
CREATE TABLE IF NOT EXISTS in_app_notifications (
    id SERIAL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 消息内容
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,              -- 'sentiment_report', 'premarket_report', 'backtest_result', 'system_alert'

    -- 状态
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,

    -- 优先级
    priority VARCHAR(20) DEFAULT 'normal',               -- 'high', 'normal', 'low'

    -- 关联数据
    business_date DATE,
    reference_id VARCHAR(100),
    metadata JSONB,                                       -- 额外数据 (JSON格式)

    -- 过期时间
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

    CONSTRAINT valid_priority CHECK (priority IN ('high', 'normal', 'low'))
);

-- 索引（在转换为 hypertable 前创建）
CREATE INDEX IF NOT EXISTS idx_in_app_notifications_user_id_unread ON in_app_notifications(user_id, is_read, created_at DESC) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_in_app_notifications_created_at ON in_app_notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_in_app_notifications_expires_at ON in_app_notifications(expires_at) WHERE expires_at IS NOT NULL;

COMMENT ON TABLE in_app_notifications IS '站内消息表（用户通知中心，时序分区表）';
COMMENT ON COLUMN in_app_notifications.priority IS '优先级：high=高, normal=普通, low=低';

-- 转换为 TimescaleDB Hypertable（按月分区）
SELECT create_hypertable('in_app_notifications', 'created_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- 自动清理 3 个月前的已读消息
-- 注意：保留策略需要更复杂的逻辑，暂时手动清理
-- SELECT add_retention_policy('in_app_notifications', INTERVAL '3 months', if_not_exists => TRUE);


-- =====================================================
-- 自动更新 updated_at 触发器
-- =====================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要的表添加触发器
DROP TRIGGER IF EXISTS update_notification_channel_configs_updated_at ON notification_channel_configs;
CREATE TRIGGER update_notification_channel_configs_updated_at
BEFORE UPDATE ON notification_channel_configs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_notification_settings_updated_at ON user_notification_settings;
CREATE TRIGGER update_user_notification_settings_updated_at
BEFORE UPDATE ON user_notification_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_notification_logs_updated_at ON notification_logs;
CREATE TRIGGER update_notification_logs_updated_at
BEFORE UPDATE ON notification_logs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================
-- 初始化说明
-- =====================================================
-- 1. notification_channel_configs: 已插入 Email 和 Telegram 默认配置（未启用）
-- 2. user_notification_settings: 新用户自动创建默认配置（触发器）
-- 3. notification_logs: 时序分区表，6个月自动清理
-- 4. in_app_notifications: 时序分区表，需手动清理已读消息

-- 验证表创建
DO $$
BEGIN
    RAISE NOTICE '✅ 通知系统表创建完成';
    RAISE NOTICE '  - notification_channel_configs (渠道配置)';
    RAISE NOTICE '  - user_notification_settings (用户订阅配置)';
    RAISE NOTICE '  - notification_logs (发送记录，时序分区)';
    RAISE NOTICE '  - in_app_notifications (站内消息，时序分区)';
END $$;
