-- =====================================================
-- 统一策略表迁移脚本
-- Version: 2.0
-- Date: 2025-02-09
-- Description: 创建统一的 strategies 表,删除旧的策略表
-- =====================================================

-- ====================================================================
-- STEP 1: 删除旧表 (如果存在)
-- ====================================================================

DROP TABLE IF EXISTS strategy_configs CASCADE;
DROP TABLE IF EXISTS ai_strategies CASCADE;

-- ====================================================================
-- STEP 2: 创建新的统一 strategies 表
-- ====================================================================

CREATE TABLE IF NOT EXISTS strategies (
    -- 主键和标识
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,              -- 策略唯一标识 (如 'momentum_20d')
    display_name VARCHAR(200) NOT NULL,             -- 显示名称 (如 '动量策略 20日')

    -- 核心代码(完整 Python 类代码)
    code TEXT NOT NULL,                             -- 完整的 Python 类代码
    code_hash VARCHAR(64) NOT NULL,                 -- SHA256 校验值
    class_name VARCHAR(100) NOT NULL,               -- 类名 (如 'MomentumStrategy')

    -- 来源分类
    source_type VARCHAR(20) NOT NULL DEFAULT 'custom',
        -- 'builtin': 系统内置(动量、均值回归、多因子)
        -- 'ai': AI 生成
        -- 'custom': 用户自定义

    -- 策略元信息
    description TEXT,                               -- 策略说明
    category VARCHAR(50),                           -- 类别 (momentum/reversal/factor/ml)
    tags TEXT[],                                    -- 标签数组

    -- 默认参数(用于快速创建变体)
    default_params JSONB,                           -- 默认参数 JSON
        -- 例如: {"lookback_period": 20, "top_n": 50}

    -- 状态和验证
    validation_status VARCHAR(20) DEFAULT 'pending', -- pending/passed/failed/validating
    validation_errors JSONB,                        -- 验证错误详情
    validation_warnings JSONB,                      -- 验证警告
    risk_level VARCHAR(20) DEFAULT 'medium',        -- safe/low/medium/high
    is_enabled BOOLEAN DEFAULT TRUE,

    -- 使用统计
    usage_count INT DEFAULT 0,                      -- 使用次数
    backtest_count INT DEFAULT 0,                   -- 回测次数
    avg_sharpe_ratio DECIMAL(10, 4),                -- 平均夏普率
    avg_annual_return DECIMAL(10, 4),               -- 平均年化收益

    -- 版本和审计
    version INT DEFAULT 1,
    parent_strategy_id INT REFERENCES strategies(id),  -- 父策略ID(变体关系)
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,

    -- 约束
    CONSTRAINT chk_source_type CHECK (source_type IN ('builtin', 'ai', 'custom')),
    CONSTRAINT chk_validation_status CHECK (validation_status IN ('pending', 'passed', 'failed', 'validating')),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('safe', 'low', 'medium', 'high'))
);

-- ====================================================================
-- STEP 3: 创建索引
-- ====================================================================

-- 基础索引
CREATE INDEX IF NOT EXISTS idx_strategies_source_type ON strategies(source_type);
CREATE INDEX IF NOT EXISTS idx_strategies_category ON strategies(category);
CREATE INDEX IF NOT EXISTS idx_strategies_enabled_validated ON strategies(is_enabled, validation_status);
CREATE INDEX IF NOT EXISTS idx_strategies_created_at ON strategies(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_strategies_usage_count ON strategies(usage_count DESC);

-- 全文搜索索引
CREATE INDEX IF NOT EXISTS idx_strategies_search ON strategies
    USING gin(to_tsvector('english', display_name || ' ' || COALESCE(description, '')));

-- GIN索引用于tags数组搜索
CREATE INDEX IF NOT EXISTS idx_strategies_tags ON strategies USING gin(tags);

-- ====================================================================
-- STEP 4: 创建更新触发器
-- ====================================================================

-- 自动更新 updated_at 时间戳
CREATE OR REPLACE FUNCTION update_strategies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_strategies_updated_at
    BEFORE UPDATE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_strategies_updated_at();

-- ====================================================================
-- STEP 5: 添加注释
-- ====================================================================

COMMENT ON TABLE strategies IS '统一策略表 - 存储所有类型的策略(内置/AI/自定义)';
COMMENT ON COLUMN strategies.code IS '完整的Python类代码字符串';
COMMENT ON COLUMN strategies.code_hash IS 'SHA256哈希,用于验证代码完整性';
COMMENT ON COLUMN strategies.source_type IS '策略来源: builtin(内置)/ai(AI生成)/custom(自定义)';
COMMENT ON COLUMN strategies.validation_status IS '代码验证状态';
COMMENT ON COLUMN strategies.default_params IS '默认参数配置,用于快速创建变体';
COMMENT ON COLUMN strategies.parent_strategy_id IS '父策略ID,用于追踪策略变体关系';

-- ====================================================================
-- 迁移完成
-- ====================================================================

-- 验证表结构
SELECT
    'Migration 008 completed successfully' AS status,
    COUNT(*) AS total_strategies
FROM strategies;
