-- =============================================
-- LLM提示词模板管理系统
--
-- 功能：
-- 1. 管理所有业务场景的提示词模板（市场情绪分析、盘前分析、策略生成等）
-- 2. 支持版本控制和历史追踪
-- 3. 支持变量占位符和动态渲染
-- 4. 统计模板性能指标（成功率、平均耗时、token消耗等）
--
-- 作者: Backend Team
-- 创建时间: 2026-03-11
-- =============================================

-- 提示词模板表
CREATE TABLE IF NOT EXISTS llm_prompt_templates (
    id SERIAL PRIMARY KEY,

    -- 业务标识
    business_type VARCHAR(50) NOT NULL,  -- sentiment_analysis, premarket_analysis, strategy_generation
    template_name VARCHAR(100) NOT NULL, -- 模板名称（如"四维度灵魂拷问v1"）
    template_key VARCHAR(100) NOT NULL,  -- 唯一标识（如"soul_questioning_v1"）

    -- 模板内容
    system_prompt TEXT,                  -- 系统提示词（定义AI角色）
    user_prompt_template TEXT NOT NULL,  -- 用户提示词模板（带占位符）
    output_format TEXT,                  -- 期望的输出格式说明

    -- 变量定义（JSONB格式）
    required_variables JSONB,            -- 必填变量列表及说明
    -- 示例: {"trade_date": "交易日期", "sh_close": "上证收盘价"}

    optional_variables JSONB,            -- 可选变量列表

    -- 版本控制
    version VARCHAR(20) NOT NULL,        -- 版本号（如"1.0.0"）
    parent_template_id INTEGER,          -- 父模板ID（用于版本链）

    -- 状态控制
    is_active BOOLEAN DEFAULT true,      -- 是否启用
    is_default BOOLEAN DEFAULT false,    -- 是否为默认模板

    -- AI提供商配置
    recommended_provider VARCHAR(50),    -- 推荐的AI提供商
    recommended_model VARCHAR(100),      -- 推荐的模型
    recommended_temperature NUMERIC(3,2), -- 推荐的温度
    recommended_max_tokens INTEGER,      -- 推荐的最大token数

    -- 元信息
    description TEXT,                    -- 模板描述
    changelog TEXT,                      -- 版本变更日志
    tags TEXT[],                         -- 标签（用于分类和搜索）

    -- 性能指标（从LLM调用日志中统计）
    avg_tokens_used INTEGER,             -- 平均token消耗
    avg_generation_time NUMERIC(10,2),   -- 平均生成耗时（秒）
    success_rate NUMERIC(5,2),           -- 成功率（%）
    usage_count INTEGER DEFAULT 0,       -- 使用次数

    -- 审计字段
    created_by VARCHAR(100),             -- 创建人
    updated_by VARCHAR(100),             -- 更新人
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 约束
    CONSTRAINT unique_template_key UNIQUE (template_key),
    CONSTRAINT fk_parent_template FOREIGN KEY (parent_template_id)
        REFERENCES llm_prompt_templates(id) ON DELETE SET NULL
);

-- 提示词模板修改历史表
CREATE TABLE IF NOT EXISTS llm_prompt_template_history (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL,

    -- 变更内容
    change_type VARCHAR(20) NOT NULL,    -- created, updated, activated, deactivated, deleted
    old_content JSONB,                   -- 修改前的内容（完整快照）
    new_content JSONB,                   -- 修改后的内容
    change_summary TEXT,                 -- 变更摘要

    -- 审计
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT,                         -- 修改原因

    CONSTRAINT fk_template_history FOREIGN KEY (template_id)
        REFERENCES llm_prompt_templates(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_prompt_templates_business_type
    ON llm_prompt_templates(business_type);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_active
    ON llm_prompt_templates(is_active);

CREATE INDEX IF NOT EXISTS idx_prompt_templates_default
    ON llm_prompt_templates(business_type, is_default)
    WHERE is_default = true;

CREATE INDEX IF NOT EXISTS idx_prompt_templates_key
    ON llm_prompt_templates(template_key);

CREATE INDEX IF NOT EXISTS idx_prompt_template_history_template_id
    ON llm_prompt_template_history(template_id);

CREATE INDEX IF NOT EXISTS idx_prompt_template_history_changed_at
    ON llm_prompt_template_history(changed_at DESC);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_prompt_template_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_prompt_template_timestamp
    BEFORE UPDATE ON llm_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_prompt_template_updated_at();

-- 触发器：自动记录修改历史
CREATE OR REPLACE FUNCTION log_prompt_template_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO llm_prompt_template_history (
            template_id,
            change_type,
            new_content,
            changed_by,
            change_summary
        ) VALUES (
            NEW.id,
            'created',
            row_to_json(NEW)::jsonb,
            NEW.created_by,
            '创建模板: ' || NEW.template_name
        );
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO llm_prompt_template_history (
            template_id,
            change_type,
            old_content,
            new_content,
            changed_by,
            change_summary
        ) VALUES (
            NEW.id,
            CASE
                WHEN OLD.is_active = true AND NEW.is_active = false THEN 'deactivated'
                WHEN OLD.is_active = false AND NEW.is_active = true THEN 'activated'
                ELSE 'updated'
            END,
            row_to_json(OLD)::jsonb,
            row_to_json(NEW)::jsonb,
            NEW.updated_by,
            CASE
                WHEN OLD.is_active != NEW.is_active THEN
                    '状态变更: ' || CASE WHEN NEW.is_active THEN '启用' ELSE '停用' END
                WHEN OLD.user_prompt_template != NEW.user_prompt_template THEN '更新提示词内容'
                WHEN OLD.version != NEW.version THEN '版本升级: ' || OLD.version || ' -> ' || NEW.version
                ELSE '更新模板配置'
            END
        );
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO llm_prompt_template_history (
            template_id,
            change_type,
            old_content,
            changed_by,
            change_summary
        ) VALUES (
            OLD.id,
            'deleted',
            row_to_json(OLD)::jsonb,
            NULL,
            '删除模板: ' || OLD.template_name
        );
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_log_prompt_template_changes
    AFTER INSERT OR UPDATE OR DELETE ON llm_prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION log_prompt_template_changes();

-- 函数：确保同一业务类型只有一个默认模板
CREATE OR REPLACE FUNCTION ensure_single_default_template()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = true THEN
        -- 将同一业务类型的其他模板设为非默认
        UPDATE llm_prompt_templates
        SET is_default = false
        WHERE business_type = NEW.business_type
          AND id != NEW.id
          AND is_default = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_single_default
    BEFORE INSERT OR UPDATE ON llm_prompt_templates
    FOR EACH ROW
    WHEN (NEW.is_default = true)
    EXECUTE FUNCTION ensure_single_default_template();

-- 视图：模板统计信息（汇总性能指标）
CREATE OR REPLACE VIEW llm_prompt_template_stats AS
SELECT
    t.id,
    t.business_type,
    t.template_name,
    t.template_key,
    t.version,
    t.is_active,
    t.is_default,

    -- 从llm_call_logs聚合统计
    COUNT(l.id) AS total_calls,
    COUNT(CASE WHEN l.status = 'success' THEN 1 END) AS successful_calls,
    COUNT(CASE WHEN l.status = 'failed' THEN 1 END) AS failed_calls,

    ROUND(
        100.0 * COUNT(CASE WHEN l.status = 'success' THEN 1 END) / NULLIF(COUNT(l.id), 0),
        2
    ) AS current_success_rate,

    ROUND(AVG(l.tokens_total)) AS current_avg_tokens,
    ROUND(AVG(l.duration_ms) / 1000.0, 2) AS current_avg_duration_sec,
    ROUND(SUM(l.cost_estimate), 4) AS total_cost,

    MAX(l.created_at) AS last_used_at,

    t.created_at,
    t.updated_at
FROM llm_prompt_templates t
LEFT JOIN llm_call_logs l ON l.prompt_template_id = t.id
GROUP BY t.id;

-- 注释
COMMENT ON TABLE llm_prompt_templates IS 'LLM提示词模板表，存储所有业务场景的提示词模板';
COMMENT ON TABLE llm_prompt_template_history IS 'LLM提示词模板修改历史表，记录所有变更';
COMMENT ON COLUMN llm_prompt_templates.business_type IS '业务类型：sentiment_analysis（情绪分析）、premarket_analysis（盘前分析）、strategy_generation（策略生成）';
COMMENT ON COLUMN llm_prompt_templates.template_key IS '模板唯一标识，全局唯一，用于代码引用';
COMMENT ON COLUMN llm_prompt_templates.system_prompt IS '系统提示词，定义AI的角色和行为';
COMMENT ON COLUMN llm_prompt_templates.user_prompt_template IS '用户提示词模板，支持Jinja2语法的占位符（如{{ trade_date }}）';
COMMENT ON COLUMN llm_prompt_templates.required_variables IS 'JSONB格式的必填变量定义，key为变量名，value为说明';
COMMENT ON COLUMN llm_prompt_templates.optional_variables IS 'JSONB格式的可选变量定义';
COMMENT ON COLUMN llm_prompt_templates.is_default IS '是否为该业务类型的默认模板（同一业务类型只能有一个默认）';

-- 初始数据示例（占位，后续通过迁移脚本填充真实数据）
-- INSERT INTO llm_prompt_templates (...) VALUES (...);

COMMIT;
