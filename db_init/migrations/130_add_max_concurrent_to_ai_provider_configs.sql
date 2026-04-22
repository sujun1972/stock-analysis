-- ai_provider_configs 新增 max_concurrent 列：按 provider 限制 LLM 并发请求数
-- 语义：同一 provider 在进程内同时"在飞"的 ainvoke 不超过该值。
-- 与 rate_limit（每分钟请求数 RPM）正交，互不影响。
-- 修改后需重启 backend / celery_worker 生效（Semaphore 在进程启动时懒加载后不再变更）。

ALTER TABLE ai_provider_configs
    ADD COLUMN IF NOT EXISTS max_concurrent INTEGER;

COMMENT ON COLUMN ai_provider_configs.max_concurrent
    IS 'LLM 并发请求上限（进程内 asyncio.Semaphore）。NULL 时按 provider 内置默认：deepseek=32, openai=16, gemini=8, 其他=8。改动需重启 backend 生效。';

-- 写入默认值：DeepSeek 基本不限，Gemini 免费档 RPM 10 留余量，OpenAI 居中
UPDATE ai_provider_configs SET max_concurrent = 32 WHERE provider = 'deepseek' AND max_concurrent IS NULL;
UPDATE ai_provider_configs SET max_concurrent = 16 WHERE provider = 'openai'   AND max_concurrent IS NULL;
UPDATE ai_provider_configs SET max_concurrent = 8  WHERE provider = 'gemini'   AND max_concurrent IS NULL;
