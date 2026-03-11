-- ============================================
-- LLM调用日志系统数据库Schema
-- 创建时间: 2026-03-11
-- 功能: 记录所有LLM模型调用的详细信息
-- ============================================

-- ============================================
-- 1. 核心表: llm_call_logs
-- ============================================
CREATE TABLE IF NOT EXISTS llm_call_logs (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 调用标识
    call_id VARCHAR(50) UNIQUE NOT NULL,           -- UUID格式，唯一标识每次调用

    -- 业务关联
    business_type VARCHAR(50) NOT NULL,             -- sentiment_analysis, premarket_analysis, strategy_generation
    business_date DATE,                             -- 关联的交易日期（如有）
    business_id VARCHAR(100),                       -- 关联的业务记录ID（如有）

    -- LLM配置
    provider VARCHAR(50) NOT NULL,                  -- deepseek, gemini, openai
    model_name VARCHAR(100) NOT NULL,               -- deepseek-chat, gemini-1.5-flash, gpt-4o等
    api_base_url VARCHAR(200),                      -- API端点地址

    -- 调用参数（JSON存储，支持未来扩展）
    call_parameters JSONB NOT NULL,                 -- {
                                                    --   "temperature": 0.7,
                                                    --   "max_tokens": 4000,
                                                    --   "timeout": 60,
                                                    --   "stream": false,
                                                    --   ...其他自定义参数
                                                    -- }

    -- 输入内容
    prompt_text TEXT NOT NULL,                      -- 完整的输入prompt
    prompt_length INTEGER,                          -- prompt字符长度
    prompt_hash VARCHAR(64),                        -- SHA256哈希，用于去重检测

    -- 输出内容
    response_text TEXT,                             -- LLM返回的原始文本
    response_length INTEGER,                        -- 返回文本字符长度
    parsed_result JSONB,                            -- 解析后的结构化结果（如适用）

    -- 性能指标
    tokens_input INTEGER,                           -- 输入token数（如API返回）
    tokens_output INTEGER,                          -- 输出token数（如API返回）
    tokens_total INTEGER,                           -- 总token数

    cost_estimate NUMERIC(10,4),                    -- 预估成本（美元）

    duration_ms INTEGER,                            -- 调用耗时（毫秒）
    start_time TIMESTAMP NOT NULL,                  -- 调用开始时间
    end_time TIMESTAMP,                             -- 调用结束时间

    -- 状态信息
    status VARCHAR(20) NOT NULL,                    -- success, failed, timeout, rate_limited
    error_code VARCHAR(50),                         -- 错误代码（如果失败）
    error_message TEXT,                             -- 错误详情

    -- HTTP信息（用于调试）
    http_status_code INTEGER,                       -- HTTP响应码
    request_headers JSONB,                          -- 请求头（脱敏后）
    response_headers JSONB,                         -- 响应头

    -- 元数据
    caller_service VARCHAR(100),                    -- 调用的服务名称
    caller_function VARCHAR(100),                   -- 调用的函数名称
    user_id VARCHAR(50),                            -- 触发用户（如果是手动触发）
    is_scheduled BOOLEAN DEFAULT false,             -- 是否为定时任务触发
    retry_count INTEGER DEFAULT 0,                  -- 重试次数
    parent_call_id VARCHAR(50),                     -- 父调用ID（如果是重试）

    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- 索引优化
-- ============================================
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_call_id ON llm_call_logs(call_id);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_business_type ON llm_call_logs(business_type);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_business_date ON llm_call_logs(business_date);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_provider ON llm_call_logs(provider);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_status ON llm_call_logs(status);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_created_at ON llm_call_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_start_time ON llm_call_logs(start_time DESC);

-- 组合索引（用于管理后台查询）
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_business_provider ON llm_call_logs(business_type, provider, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_call_logs_date_status ON llm_call_logs(business_date, status);

-- ============================================
-- 表注释
-- ============================================
COMMENT ON TABLE llm_call_logs IS 'LLM调用日志表，记录所有AI模型调用的详细信息';
COMMENT ON COLUMN llm_call_logs.call_id IS '全局唯一调用ID（UUID格式）';
COMMENT ON COLUMN llm_call_logs.business_type IS '业务类型：sentiment_analysis, premarket_analysis, strategy_generation';
COMMENT ON COLUMN llm_call_logs.call_parameters IS 'JSON格式的调用参数，包括temperature、max_tokens等';
COMMENT ON COLUMN llm_call_logs.prompt_hash IS 'Prompt的SHA256哈希，用于检测重复调用';
COMMENT ON COLUMN llm_call_logs.cost_estimate IS '基于token数预估的调用成本（美元）';


-- ============================================
-- 2. 统计视图: llm_call_statistics_daily
-- ============================================
CREATE OR REPLACE VIEW llm_call_statistics_daily AS
SELECT
    DATE(created_at) AS stat_date,
    business_type,
    provider,
    model_name,

    -- 调用次数
    COUNT(*) AS total_calls,
    COUNT(*) FILTER (WHERE status = 'success') AS success_calls,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_calls,

    -- 成功率
    ROUND(COUNT(*) FILTER (WHERE status = 'success')::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS success_rate,

    -- Token统计
    SUM(tokens_total) AS total_tokens,
    AVG(tokens_total) AS avg_tokens_per_call,
    MAX(tokens_total) AS max_tokens,

    -- 成本统计
    SUM(cost_estimate) AS total_cost,
    AVG(cost_estimate) AS avg_cost_per_call,

    -- 性能统计
    AVG(duration_ms) AS avg_duration_ms,
    MIN(duration_ms) AS min_duration_ms,
    MAX(duration_ms) AS max_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_duration_ms,

    -- 重试统计
    SUM(retry_count) AS total_retries,
    AVG(retry_count) AS avg_retry_per_call

FROM llm_call_logs
GROUP BY DATE(created_at), business_type, provider, model_name
ORDER BY stat_date DESC, total_calls DESC;

COMMENT ON VIEW llm_call_statistics_daily IS 'LLM调用每日统计视图';


-- ============================================
-- 3. 成本配置表: llm_pricing_config
-- ============================================
CREATE TABLE IF NOT EXISTS llm_pricing_config (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,

    -- 价格（每百万token的美元价格）
    input_price_per_million NUMERIC(10,4),      -- 输入token价格
    output_price_per_million NUMERIC(10,4),     -- 输出token价格

    effective_from DATE NOT NULL,               -- 生效日期
    effective_to DATE,                          -- 失效日期（NULL表示永久有效）

    currency VARCHAR(10) DEFAULT 'USD',
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(provider, model_name, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_llm_pricing_provider_model ON llm_pricing_config(provider, model_name, effective_from DESC);

COMMENT ON TABLE llm_pricing_config IS 'LLM定价配置表，用于成本估算';


-- ============================================
-- 4. 初始化价格数据（2025年价格）
-- ============================================
INSERT INTO llm_pricing_config (provider, model_name, input_price_per_million, output_price_per_million, effective_from, notes)
VALUES
    ('deepseek', 'deepseek-chat', 1.0, 2.0, '2025-01-01', 'DeepSeek V3 官方价格'),
    ('gemini', 'gemini-1.5-flash', 0.075, 0.30, '2025-01-01', 'Google Gemini 1.5 Flash 价格'),
    ('openai', 'gpt-4o', 2.50, 10.0, '2025-01-01', 'OpenAI GPT-4o 价格'),
    ('openai', 'gpt-4o-mini', 0.15, 0.60, '2025-01-01', 'OpenAI GPT-4o mini 价格')
ON CONFLICT (provider, model_name, effective_from) DO NOTHING;


-- ============================================
-- 5. 触发器：自动更新updated_at
-- ============================================
CREATE OR REPLACE FUNCTION update_llm_call_logs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_llm_call_logs_updated_at ON llm_call_logs;
CREATE TRIGGER trigger_update_llm_call_logs_updated_at
    BEFORE UPDATE ON llm_call_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_llm_call_logs_updated_at();


-- ============================================
-- 完成提示
-- ============================================
DO $$
BEGIN
    RAISE NOTICE '✅ LLM调用日志系统数据库Schema创建完成！';
    RAISE NOTICE '   - llm_call_logs 表已创建（含索引）';
    RAISE NOTICE '   - llm_call_statistics_daily 视图已创建';
    RAISE NOTICE '   - llm_pricing_config 表已创建（含初始价格数据）';
END $$;
