-- ================================================
-- 池化训练和Ridge基准对比功能 - 数据库Schema扩展
-- ================================================

-- 为 experiments 表添加池化训练相关字段

-- 1. 是否包含Ridge基准对比
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS has_baseline BOOLEAN DEFAULT FALSE;

-- 2. Ridge基准模型的指标
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS baseline_metrics JSONB;

-- 3. Ridge vs LightGBM 对比结果
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS comparison_result JSONB;

-- 4. 推荐使用的模型 ('ridge' 或 'lightgbm')
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS recommendation VARCHAR(50);

-- 5. 池化训练的总样本数
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS total_samples INTEGER;

-- 6. 成功加载的股票代码列表
ALTER TABLE experiments
ADD COLUMN IF NOT EXISTS successful_symbols TEXT[];

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_experiments_has_baseline
ON experiments(has_baseline);

CREATE INDEX IF NOT EXISTS idx_experiments_recommendation
ON experiments(recommendation);

-- 添加注释
COMMENT ON COLUMN experiments.has_baseline IS '是否包含Ridge基准对比';
COMMENT ON COLUMN experiments.baseline_metrics IS 'Ridge基准模型的评估指标（JSON格式）';
COMMENT ON COLUMN experiments.comparison_result IS 'Ridge vs LightGBM 对比结果（JSON格式）';
COMMENT ON COLUMN experiments.recommendation IS '推荐使用的模型类型';
COMMENT ON COLUMN experiments.total_samples IS '池化训练的总样本数';
COMMENT ON COLUMN experiments.successful_symbols IS '成功加载的股票代码数组';

-- 验证表结构
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'experiments'
AND column_name IN (
    'has_baseline',
    'baseline_metrics',
    'comparison_result',
    'recommendation',
    'total_samples',
    'successful_symbols'
)
ORDER BY ordinal_position;
