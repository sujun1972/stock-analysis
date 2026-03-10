-- 修复AI提供商配置表的temperature字段类型
-- 问题：temperature字段原本是INTEGER类型，无法存储小数值（如0.7）
-- 解决：将字段类型改为NUMERIC(3,2)，支持0.00-9.99范围的小数

-- 修改字段类型
ALTER TABLE ai_provider_configs
ALTER COLUMN temperature TYPE NUMERIC(3,2);

-- 确保所有现有配置的temperature值在有效范围内
-- DeepSeek API要求: [0, 2]
-- OpenAI API要求: [0, 2]
-- Gemini API要求: [0, 1]
UPDATE ai_provider_configs
SET temperature = 0.7
WHERE temperature IS NULL OR temperature > 2 OR temperature < 0;

-- 添加约束确保temperature值在合理范围内
ALTER TABLE ai_provider_configs
ADD CONSTRAINT check_temperature_range
CHECK (temperature >= 0 AND temperature <= 2);

COMMENT ON COLUMN ai_provider_configs.temperature IS 'AI模型温度参数，范围[0, 2]，控制生成随机性。0=确定性，2=最大随机性';
