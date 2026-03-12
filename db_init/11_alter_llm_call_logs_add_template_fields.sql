-- =============================================
-- 修改 llm_call_logs 表，添加提示词模板关联字段
--
-- 功能：
-- 将LLM调用日志与提示词模板关联，用于统计模板性能
--
-- 作者: Backend Team
-- 创建时间: 2026-03-11
-- =============================================

-- 添加提示词模板关联字段
ALTER TABLE llm_call_logs
ADD COLUMN IF NOT EXISTS prompt_template_id INTEGER,
ADD COLUMN IF NOT EXISTS prompt_template_version VARCHAR(20);

-- 添加外键约束
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_llm_call_logs_prompt_template'
    ) THEN
        ALTER TABLE llm_call_logs
        ADD CONSTRAINT fk_llm_call_logs_prompt_template
            FOREIGN KEY (prompt_template_id)
            REFERENCES llm_prompt_templates(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_template_id
    ON llm_call_logs(prompt_template_id);

CREATE INDEX IF NOT EXISTS idx_llm_call_logs_template_version
    ON llm_call_logs(prompt_template_id, prompt_template_version);

-- 注释
COMMENT ON COLUMN llm_call_logs.prompt_template_id IS '关联的提示词模板ID';
COMMENT ON COLUMN llm_call_logs.prompt_template_version IS '使用的提示词模板版本号';

COMMIT;
