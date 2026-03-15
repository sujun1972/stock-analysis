-- Phase 2: 通知系统增强 - 模板表和频率限制字段
-- 执行日期: 2026-03-15

-- ============================================
-- 1. 创建通知模板表
-- ============================================

CREATE TABLE IF NOT EXISTS notification_templates (
    id SERIAL PRIMARY KEY,

    -- 模板标识
    template_name VARCHAR(100) NOT NULL UNIQUE,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,                        -- 'email', 'telegram', 'in_app'

    -- 模板内容
    subject_template TEXT,                                -- 邮件主题/消息标题模板（Jinja2）
    content_template TEXT NOT NULL,                       -- 内容模板（Jinja2）

    -- 变量说明
    available_variables JSONB,                            -- 可用变量列表（用于前端提示）
    example_data JSONB,                                   -- 示例数据（用于模板预览）

    -- 状态
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 10,                          -- 优先级（数字越小优先级越高）

    -- 描述
    description TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_notification_templates_type_channel ON notification_templates(notification_type, channel);
CREATE INDEX IF NOT EXISTS idx_notification_templates_active ON notification_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_notification_templates_name ON notification_templates(template_name);

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_notification_templates_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_notification_templates_updated_at_trigger ON notification_templates;
CREATE TRIGGER update_notification_templates_updated_at_trigger
BEFORE UPDATE ON notification_templates
FOR EACH ROW EXECUTE FUNCTION update_notification_templates_updated_at();


-- ============================================
-- 2. 插入默认模板
-- ============================================

-- 2.1 盘后情绪分析报告 - Email 模板
INSERT INTO notification_templates (
    template_name,
    notification_type,
    channel,
    subject_template,
    content_template,
    available_variables,
    example_data,
    description,
    priority
) VALUES (
    'sentiment_report_email_full',
    'sentiment_report',
    'email',
    '📊 {{ trade_date }} A股盘后情绪分析报告',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; }
        .section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-left: 4px solid #667eea; border-radius: 5px; }
        .section h2 { color: #667eea; margin-top: 0; }
        .footer { text-align: center; color: #888; padding: 20px; font-size: 12px; }
        .highlight { background: #fff3cd; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 A股盘后情绪分析报告</h1>
            <p><strong>交易日期:</strong> {{ trade_date }}</p>
        </div>

        {% if space_analysis %}
        <div class="section">
            <h2>🌌 空间：龙头高度与板块空间</h2>
            <div>{{ space_analysis | safe }}</div>
        </div>
        {% endif %}

        {% if sentiment_analysis %}
        <div class="section">
            <h2>😊 情绪：赚钱效应与市场温度</h2>
            <div>{{ sentiment_analysis | safe }}</div>
        </div>
        {% endif %}

        {% if capital_flow_analysis %}
        <div class="section">
            <h2>💰 资金：北向与游资动向</h2>
            <div>{{ capital_flow_analysis | safe }}</div>
        </div>
        {% endif %}

        {% if tomorrow_tactics %}
        <div class="section">
            <h2>🎯 战术：明日操作策略</h2>
            <div>{{ tomorrow_tactics | safe }}</div>
        </div>
        {% endif %}

        <div class="footer">
            <p>本报告由 AI 智能分析生成 | 股票分析系统</p>
            <p>生成时间: {{ generated_at }}</p>
        </div>
    </div>
</body>
</html>',
    '["trade_date", "space_analysis", "sentiment_analysis", "capital_flow_analysis", "tomorrow_tactics", "generated_at"]'::jsonb,
    '{
        "trade_date": "2026-03-15",
        "space_analysis": "今日市场高度板 3 板，龙头股票表现强势...",
        "sentiment_analysis": "赚钱效应指数 75，市场情绪偏暖...",
        "capital_flow_analysis": "北向资金净流入 50 亿...",
        "tomorrow_tactics": "明日重点关注科技板块...",
        "generated_at": "2026-03-15 18:30:00"
    }'::jsonb,
    '盘后情绪分析报告（Email 完整版）',
    1
) ON CONFLICT (template_name) DO NOTHING;


-- 2.2 盘后情绪分析报告 - Telegram 模板
INSERT INTO notification_templates (
    template_name,
    notification_type,
    channel,
    subject_template,
    content_template,
    available_variables,
    example_data,
    description,
    priority
) VALUES (
    'sentiment_report_telegram_full',
    'sentiment_report',
    'telegram',
    NULL,
    '📊 *{{ trade_date }} A股盘后情绪分析*

{% if space_analysis %}
🌌 *空间：龙头高度与板块空间*
{{ space_analysis }}

{% endif %}
{% if sentiment_analysis %}
😊 *情绪：赚钱效应与市场温度*
{{ sentiment_analysis }}

{% endif %}
{% if capital_flow_analysis %}
💰 *资金：北向与游资动向*
{{ capital_flow_analysis }}

{% endif %}
{% if tomorrow_tactics %}
🎯 *战术：明日操作策略*
{{ tomorrow_tactics }}
{% endif %}

_生成时间: {{ generated_at }}_',
    '["trade_date", "space_analysis", "sentiment_analysis", "capital_flow_analysis", "tomorrow_tactics", "generated_at"]'::jsonb,
    '{
        "trade_date": "2026-03-15",
        "space_analysis": "今日市场高度板 3 板",
        "sentiment_analysis": "赚钱效应指数 75",
        "capital_flow_analysis": "北向资金净流入 50 亿",
        "tomorrow_tactics": "明日重点关注科技板块",
        "generated_at": "2026-03-15 18:30:00"
    }'::jsonb,
    '盘后情绪分析报告（Telegram 完整版）',
    1
) ON CONFLICT (template_name) DO NOTHING;


-- 2.3 盘后情绪分析报告 - 站内消息模板
INSERT INTO notification_templates (
    template_name,
    notification_type,
    channel,
    subject_template,
    content_template,
    available_variables,
    example_data,
    description,
    priority
) VALUES (
    'sentiment_report_in_app_summary',
    'sentiment_report',
    'in_app',
    '{{ trade_date }} 盘后情绪分析',
    '{% if space_analysis %}**空间:** {{ space_analysis }}

{% endif %}{% if sentiment_analysis %}**情绪:** {{ sentiment_analysis }}

{% endif %}{% if capital_flow_analysis %}**资金:** {{ capital_flow_analysis }}

{% endif %}{% if tomorrow_tactics %}**战术:** {{ tomorrow_tactics }}{% endif %}',
    '["trade_date", "space_analysis", "sentiment_analysis", "capital_flow_analysis", "tomorrow_tactics"]'::jsonb,
    '{
        "trade_date": "2026-03-15",
        "space_analysis": "高度板 3 板",
        "sentiment_analysis": "赚钱效应 75",
        "capital_flow_analysis": "北向净流入 50 亿",
        "tomorrow_tactics": "关注科技板块"
    }'::jsonb,
    '盘后情绪分析报告（站内消息摘要版）',
    1
) ON CONFLICT (template_name) DO NOTHING;


-- 2.4 盘前碰撞分析报告 - Email 模板
INSERT INTO notification_templates (
    template_name,
    notification_type,
    channel,
    subject_template,
    content_template,
    available_variables,
    example_data,
    description,
    priority
) VALUES (
    'premarket_report_email_full',
    'premarket_report',
    'email',
    '🌅 {{ trade_date }} A股盘前碰撞分析',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; border-radius: 10px; }
        .section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-left: 4px solid #f5576c; border-radius: 5px; }
        .section h2 { color: #f5576c; margin-top: 0; }
        .footer { text-align: center; color: #888; padding: 20px; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌅 A股盘前碰撞分析</h1>
            <p><strong>交易日期:</strong> {{ trade_date }}</p>
        </div>

        {% if macro_tone %}
        <div class="section">
            <h2>🌍 宏观定调</h2>
            <div>{{ macro_tone | safe }}</div>
        </div>
        {% endif %}

        {% if position_check %}
        <div class="section">
            <h2>⚠️ 持仓排雷</h2>
            <div>{{ position_check | safe }}</div>
        </div>
        {% endif %}

        {% if plan_adjustment %}
        <div class="section">
            <h2>📝 计划修正</h2>
            <div>{{ plan_adjustment | safe }}</div>
        </div>
        {% endif %}

        {% if bidding_watch %}
        <div class="section">
            <h2>👁️ 竞价盯盘</h2>
            <div>{{ bidding_watch | safe }}</div>
        </div>
        {% endif %}

        <div class="footer">
            <p>本报告由 AI 智能分析生成 | 股票分析系统</p>
            <p>生成时间: {{ generated_at }}</p>
        </div>
    </div>
</body>
</html>',
    '["trade_date", "macro_tone", "position_check", "plan_adjustment", "bidding_watch", "generated_at"]'::jsonb,
    '{
        "trade_date": "2026-03-15",
        "macro_tone": "隔夜美股上涨，A股预期偏暖",
        "position_check": "持仓个股未发现重大利空",
        "plan_adjustment": "建议关注科技板块",
        "bidding_watch": "重点观察集合竞价强度",
        "generated_at": "2026-03-15 08:00:00"
    }'::jsonb,
    '盘前碰撞分析报告（Email 完整版）',
    2
) ON CONFLICT (template_name) DO NOTHING;


-- 2.5 回测完成通知 - Telegram 模板
INSERT INTO notification_templates (
    template_name,
    notification_type,
    channel,
    subject_template,
    content_template,
    available_variables,
    example_data,
    description,
    priority
) VALUES (
    'backtest_result_telegram_summary',
    'backtest_result',
    'telegram',
    NULL,
    '🎯 *回测任务完成*

*策略名称:* {{ strategy_name }}
*回测周期:* {{ start_date }} ~ {{ end_date }}

📈 *绩效指标*
• 累计收益: {{ total_return }}%
• 年化收益: {{ annual_return }}%
• 最大回撤: {{ max_drawdown }}%
• 夏普比率: {{ sharpe_ratio }}
• 胜率: {{ win_rate }}%

_完成时间: {{ completed_at }}_',
    '["strategy_name", "start_date", "end_date", "total_return", "annual_return", "max_drawdown", "sharpe_ratio", "win_rate", "completed_at"]'::jsonb,
    '{
        "strategy_name": "动量策略 v1.0",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "total_return": "25.5",
        "annual_return": "25.5",
        "max_drawdown": "12.3",
        "sharpe_ratio": "1.85",
        "win_rate": "62.5",
        "completed_at": "2026-03-15 14:30:00"
    }'::jsonb,
    '回测完成通知（Telegram 摘要版）',
    3
) ON CONFLICT (template_name) DO NOTHING;


-- ============================================
-- 3. 为用户通知配置表添加频率限制字段
-- ============================================

-- 检查表是否存在，如果存在则添加新字段
DO $$
BEGIN
    -- 添加通知频率控制字段
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_notification_settings') THEN
        -- 每日通知计数器（在触发器中自动重置）
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'user_notification_settings'
                      AND column_name = 'daily_notification_count') THEN
            ALTER TABLE user_notification_settings
            ADD COLUMN daily_notification_count INTEGER DEFAULT 0;
        END IF;

        -- 上次重置时间
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'user_notification_settings'
                      AND column_name = 'last_reset_date') THEN
            ALTER TABLE user_notification_settings
            ADD COLUMN last_reset_date DATE DEFAULT CURRENT_DATE;
        END IF;

        -- 是否启用频率限制
        IF NOT EXISTS (SELECT FROM information_schema.columns
                      WHERE table_name = 'user_notification_settings'
                      AND column_name = 'enable_rate_limit') THEN
            ALTER TABLE user_notification_settings
            ADD COLUMN enable_rate_limit BOOLEAN DEFAULT true;
        END IF;
    END IF;
END $$;


-- ============================================
-- 4. 创建频率限制辅助表（可选）
-- ============================================

CREATE TABLE IF NOT EXISTS notification_rate_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_date DATE NOT NULL DEFAULT CURRENT_DATE,

    -- 各渠道发送计数
    email_count INTEGER DEFAULT 0,
    telegram_count INTEGER DEFAULT 0,
    in_app_count INTEGER DEFAULT 0,
    total_count INTEGER DEFAULT 0,

    -- 时间窗口统计（每小时）
    hourly_counts JSONB DEFAULT '{}'::jsonb,  -- {"00": 2, "01": 0, ...}

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, notification_date)
);

CREATE INDEX IF NOT EXISTS idx_notification_rate_limits_user_date ON notification_rate_limits(user_id, notification_date);

-- 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_notification_rate_limits_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_notification_rate_limits_updated_at_trigger ON notification_rate_limits;
CREATE TRIGGER update_notification_rate_limits_updated_at_trigger
BEFORE UPDATE ON notification_rate_limits
FOR EACH ROW EXECUTE FUNCTION update_notification_rate_limits_updated_at();


-- ============================================
-- 5. 验证和输出
-- ============================================

-- 检查模板表创建情况
SELECT
    COUNT(*) as template_count,
    COUNT(DISTINCT channel) as channel_count,
    COUNT(DISTINCT notification_type) as notification_type_count
FROM notification_templates;

-- 输出创建的模板列表
SELECT
    template_name,
    notification_type,
    channel,
    is_active,
    description
FROM notification_templates
ORDER BY notification_type, channel, priority;

COMMENT ON TABLE notification_templates IS 'Phase 2: 通知模板表（支持 Jinja2 动态��染）';
COMMENT ON TABLE notification_rate_limits IS 'Phase 2: 通知频率限制记录表';
