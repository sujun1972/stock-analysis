-- ============================================================
-- Backend适配Core v6.0 - 新增策略表
-- 创建时间: 2026-02-09
-- Phase 2: 新增数据库表
-- 说明: 支持配置驱动策略和动态代码策略
-- ============================================================

-- ============================================================
-- 1. 策略配置表 (Configured Strategies)
-- ============================================================
-- 用于存储配置驱动策略的参数配置
-- 对应 Core v6.0 的 StrategyFactory.create_from_config()
CREATE TABLE IF NOT EXISTS strategy_configs (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    strategy_type VARCHAR(50) NOT NULL,              -- 预定义策略类型: 'momentum', 'mean_reversion', 'multi_factor'
    config JSONB NOT NULL,                           -- 策略参数配置 (JSON格式)

    -- 元数据
    name VARCHAR(200),                               -- 配置名称（用户自定义）
    description TEXT,                                -- 配置说明
    category VARCHAR(50),                            -- 分类（如: aggressive, conservative, balanced）
    tags VARCHAR(100)[],                             -- 标签数组，便于分类和搜索

    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,                 -- 是否启用
    status VARCHAR(20) DEFAULT 'active',             -- active, archived, deprecated

    -- 版本控制
    version INT DEFAULT 1,                           -- 版本号
    parent_id INT REFERENCES strategy_configs(id),   -- 父配置ID（用于版本追溯）

    -- 绩效指标 (最近一次回测结果)
    last_backtest_metrics JSONB,                     -- 最近回测指标
    last_backtest_date TIMESTAMP,                    -- 最近回测时间

    -- 审计字段
    created_by VARCHAR(100),                         -- 创建人
    created_at TIMESTAMP DEFAULT NOW(),              -- 创建时间
    updated_by VARCHAR(100),                         -- 更新人
    updated_at TIMESTAMP DEFAULT NOW(),              -- 更新时间

    -- 约束
    CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN ('momentum', 'mean_reversion', 'multi_factor')
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('active', 'archived', 'deprecated')
    )
);

-- 为策略配置表创建索引
CREATE INDEX idx_strategy_configs_type ON strategy_configs(strategy_type);
CREATE INDEX idx_strategy_configs_enabled ON strategy_configs(is_enabled);
CREATE INDEX idx_strategy_configs_status ON strategy_configs(status);
CREATE INDEX idx_strategy_configs_created ON strategy_configs(created_at DESC);
CREATE INDEX idx_strategy_configs_tags ON strategy_configs USING GIN(tags);
CREATE INDEX idx_strategy_configs_config ON strategy_configs USING GIN(config);  -- 支持JSONB查询

-- 添加触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_strategy_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_strategy_configs_updated_at
    BEFORE UPDATE ON strategy_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_strategy_configs_updated_at();


-- ============================================================
-- 2. 动态代码策略表 (Dynamic Strategies)
-- ============================================================
-- 用于存储动态加载的Python策略代码（支持AI生成）
-- 对应 Core v6.0 的 StrategyFactory.create_from_code()
CREATE TABLE IF NOT EXISTS dynamic_strategies (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    strategy_name VARCHAR(200) NOT NULL UNIQUE,     -- 策略名称（唯一标识）
    display_name VARCHAR(200),                      -- 显示名称
    description TEXT,                               -- 策略说明
    class_name VARCHAR(100) NOT NULL,               -- Python类名

    -- 代码
    generated_code TEXT NOT NULL,                   -- Python策略类代码
    code_hash VARCHAR(64),                          -- 代码的SHA256哈希值

    -- AI生成信息 (如果适用)
    user_prompt TEXT,                               -- 用户的自然语言描述
    ai_model VARCHAR(50),                           -- AI模型名称: 'deepseek-coder', 'gpt-4', etc.
    ai_prompt TEXT,                                 -- 完整的AI Prompt
    generation_tokens INT,                          -- Token消耗
    generation_cost DECIMAL(10, 4),                 -- 生成成本

    -- 验证状态
    validation_status VARCHAR(20) DEFAULT 'pending', -- pending, passed, failed, warning
    validation_errors JSONB,                        -- 验证错误信息（数组）
    validation_warnings JSONB,                      -- 验证警告信息（数组）

    -- 测试结果
    test_status VARCHAR(20),                        -- untested, passed, failed
    test_results JSONB,                             -- 测试结果详情

    -- 绩效指标
    last_backtest_metrics JSONB,                    -- 最近回测指标
    last_backtest_date TIMESTAMP,                   -- 最近回测时间

    -- 状态
    is_enabled BOOLEAN DEFAULT TRUE,                -- 是否启用
    status VARCHAR(20) DEFAULT 'draft',             -- draft, active, archived, deprecated

    -- 版本控制
    version INT DEFAULT 1,                          -- 版本号
    parent_id INT REFERENCES dynamic_strategies(id), -- 父策略ID（用于版本追溯）

    -- 审计字段
    created_by VARCHAR(100),                        -- 创建人
    created_at TIMESTAMP DEFAULT NOW(),             -- 创建时间
    updated_by VARCHAR(100),                        -- 更新人
    updated_at TIMESTAMP DEFAULT NOW(),             -- 更新时间

    -- 元数据
    tags VARCHAR(100)[],                            -- 标签数组
    category VARCHAR(50),                           -- 分类

    -- 约束
    CONSTRAINT valid_validation_status CHECK (
        validation_status IN ('pending', 'passed', 'failed', 'warning')
    ),
    CONSTRAINT valid_dynamic_status CHECK (
        status IN ('draft', 'active', 'archived', 'deprecated')
    ),
    CONSTRAINT valid_test_status CHECK (
        test_status IS NULL OR test_status IN ('untested', 'passed', 'failed')
    )
);

-- 为动态策略表创建索引
CREATE INDEX idx_dynamic_strat_name ON dynamic_strategies(strategy_name);
CREATE INDEX idx_dynamic_strat_class ON dynamic_strategies(class_name);
CREATE INDEX idx_dynamic_strat_enabled ON dynamic_strategies(is_enabled);
CREATE INDEX idx_dynamic_strat_validation ON dynamic_strategies(validation_status);
CREATE INDEX idx_dynamic_strat_status ON dynamic_strategies(status);
CREATE INDEX idx_dynamic_strat_created ON dynamic_strategies(created_at DESC);
CREATE INDEX idx_dynamic_strat_tags ON dynamic_strategies USING GIN(tags);

-- 添加触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_dynamic_strategies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_dynamic_strategies_updated_at
    BEFORE UPDATE ON dynamic_strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_dynamic_strategies_updated_at();


-- ============================================================
-- 3. 策略执行记录表 (Strategy Executions)
-- ============================================================
-- 统一记录所有类型策略的执行情况（回测、模拟交易、实盘）
CREATE TABLE IF NOT EXISTS strategy_executions (
    id BIGSERIAL PRIMARY KEY,

    -- 策略引用 (三选一)
    predefined_strategy_type VARCHAR(50),            -- 预定义策略: 'momentum', 'mean_reversion', etc.
    config_strategy_id INT REFERENCES strategy_configs(id) ON DELETE SET NULL,
    dynamic_strategy_id INT REFERENCES dynamic_strategies(id) ON DELETE SET NULL,

    -- 执行类型
    execution_type VARCHAR(20) NOT NULL,             -- backtest, paper_trading, live_trading, validation

    -- 执行参数
    execution_params JSONB NOT NULL,                 -- 执行参数（股票池、时间范围、初始资金等）

    -- 执行结果
    status VARCHAR(20) DEFAULT 'pending',            -- pending, running, completed, failed, cancelled
    result JSONB,                                    -- 完整结果数据
    metrics JSONB,                                   -- 关键指标
    error_message TEXT,                              -- 错误信息

    -- 性能统计
    execution_duration_ms INT,                       -- 执行耗时（毫秒）

    -- 审计字段
    executed_by VARCHAR(100),                        -- 执行人
    started_at TIMESTAMP,                            -- 开始时间
    completed_at TIMESTAMP,                          -- 完成时间
    created_at TIMESTAMP DEFAULT NOW(),              -- 创建时间

    -- 约束
    CONSTRAINT valid_exec_type CHECK (
        execution_type IN ('backtest', 'paper_trading', 'live_trading', 'validation')
    ),
    CONSTRAINT valid_exec_status CHECK (
        status IN ('pending', 'running', 'completed', 'failed', 'cancelled')
    ),
    -- 确保至少有一个策略类型被设置
    CONSTRAINT at_least_one_strategy CHECK (
        (predefined_strategy_type IS NOT NULL)::int +
        (config_strategy_id IS NOT NULL)::int +
        (dynamic_strategy_id IS NOT NULL)::int = 1
    )
);

-- 为策略执行表创建索引
CREATE INDEX idx_exec_config_strat ON strategy_executions(config_strategy_id, created_at DESC);
CREATE INDEX idx_exec_dynamic_strat ON strategy_executions(dynamic_strategy_id, created_at DESC);
CREATE INDEX idx_exec_predefined ON strategy_executions(predefined_strategy_type, created_at DESC);
CREATE INDEX idx_exec_type ON strategy_executions(execution_type);
CREATE INDEX idx_exec_status ON strategy_executions(status);
CREATE INDEX idx_exec_created ON strategy_executions(created_at DESC);


-- ============================================================
-- 4. 视图: 策略配置性能排行榜
-- ============================================================
CREATE OR REPLACE VIEW strategy_configs_leaderboard AS
SELECT
    sc.id,
    sc.strategy_type,
    sc.name,
    sc.description,
    sc.is_enabled,
    sc.status,
    sc.last_backtest_metrics,
    sc.last_backtest_date,

    -- 解析关键指标
    (sc.last_backtest_metrics->>'annual_return')::FLOAT AS annual_return,
    (sc.last_backtest_metrics->>'sharpe_ratio')::FLOAT AS sharpe_ratio,
    (sc.last_backtest_metrics->>'max_drawdown')::FLOAT AS max_drawdown,
    (sc.last_backtest_metrics->>'win_rate')::FLOAT AS win_rate,

    -- 执行统计
    (SELECT COUNT(*) FROM strategy_executions se
     WHERE se.config_strategy_id = sc.id) AS total_executions,
    (SELECT COUNT(*) FROM strategy_executions se
     WHERE se.config_strategy_id = sc.id AND se.status = 'completed') AS successful_executions,

    sc.created_at,
    sc.updated_at
FROM strategy_configs sc
WHERE sc.is_enabled = TRUE
ORDER BY
    (sc.last_backtest_metrics->>'sharpe_ratio')::FLOAT DESC NULLS LAST,
    sc.last_backtest_date DESC NULLS LAST;


-- ============================================================
-- 5. 视图: 动态策略性能排行榜
-- ============================================================
CREATE OR REPLACE VIEW dynamic_strategies_leaderboard AS
SELECT
    ds.id,
    ds.strategy_name,
    ds.display_name,
    ds.description,
    ds.class_name,
    ds.validation_status,
    ds.test_status,
    ds.is_enabled,
    ds.status,
    ds.last_backtest_metrics,
    ds.last_backtest_date,

    -- 解析关键指标
    (ds.last_backtest_metrics->>'annual_return')::FLOAT AS annual_return,
    (ds.last_backtest_metrics->>'sharpe_ratio')::FLOAT AS sharpe_ratio,
    (ds.last_backtest_metrics->>'max_drawdown')::FLOAT AS max_drawdown,
    (ds.last_backtest_metrics->>'win_rate')::FLOAT AS win_rate,

    -- AI生成信息
    ds.ai_model,
    ds.user_prompt,

    -- 执行统计
    (SELECT COUNT(*) FROM strategy_executions se
     WHERE se.dynamic_strategy_id = ds.id) AS total_executions,
    (SELECT COUNT(*) FROM strategy_executions se
     WHERE se.dynamic_strategy_id = ds.id AND se.status = 'completed') AS successful_executions,

    ds.created_at,
    ds.updated_at
FROM dynamic_strategies ds
WHERE ds.is_enabled = TRUE
  AND ds.validation_status IN ('passed', 'warning')
ORDER BY
    (ds.last_backtest_metrics->>'sharpe_ratio')::FLOAT DESC NULLS LAST,
    ds.last_backtest_date DESC NULLS LAST;


-- ============================================================
-- 6. 函数: 获取Top配置策略
-- ============================================================
CREATE OR REPLACE FUNCTION get_top_config_strategies(
    p_strategy_type VARCHAR DEFAULT NULL,
    p_top_n INT DEFAULT 10,
    p_min_sharpe FLOAT DEFAULT NULL,
    p_max_drawdown FLOAT DEFAULT NULL
)
RETURNS TABLE (
    config_id INT,
    strategy_type VARCHAR,
    config_name VARCHAR,
    annual_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    win_rate FLOAT,
    last_backtest_date TIMESTAMP,
    config JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        sc.id,
        sc.strategy_type,
        sc.name,
        (sc.last_backtest_metrics->>'annual_return')::FLOAT,
        (sc.last_backtest_metrics->>'sharpe_ratio')::FLOAT,
        (sc.last_backtest_metrics->>'max_drawdown')::FLOAT,
        (sc.last_backtest_metrics->>'win_rate')::FLOAT,
        sc.last_backtest_date,
        sc.config
    FROM strategy_configs sc
    WHERE
        sc.is_enabled = TRUE
        AND sc.status = 'active'
        AND sc.last_backtest_metrics IS NOT NULL
        AND (p_strategy_type IS NULL OR sc.strategy_type = p_strategy_type)
        AND (p_min_sharpe IS NULL OR (sc.last_backtest_metrics->>'sharpe_ratio')::FLOAT >= p_min_sharpe)
        AND (p_max_drawdown IS NULL OR (sc.last_backtest_metrics->>'max_drawdown')::FLOAT >= p_max_drawdown)
    ORDER BY (sc.last_backtest_metrics->>'sharpe_ratio')::FLOAT DESC NULLS LAST
    LIMIT p_top_n;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 7. 函数: 获取Top动态策略
-- ============================================================
CREATE OR REPLACE FUNCTION get_top_dynamic_strategies(
    p_top_n INT DEFAULT 10,
    p_min_sharpe FLOAT DEFAULT NULL,
    p_max_drawdown FLOAT DEFAULT NULL
)
RETURNS TABLE (
    strategy_id INT,
    strategy_name VARCHAR,
    display_name VARCHAR,
    annual_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    win_rate FLOAT,
    validation_status VARCHAR,
    last_backtest_date TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ds.id,
        ds.strategy_name,
        ds.display_name,
        (ds.last_backtest_metrics->>'annual_return')::FLOAT,
        (ds.last_backtest_metrics->>'sharpe_ratio')::FLOAT,
        (ds.last_backtest_metrics->>'max_drawdown')::FLOAT,
        (ds.last_backtest_metrics->>'win_rate')::FLOAT,
        ds.validation_status,
        ds.last_backtest_date
    FROM dynamic_strategies ds
    WHERE
        ds.is_enabled = TRUE
        AND ds.status = 'active'
        AND ds.validation_status IN ('passed', 'warning')
        AND ds.last_backtest_metrics IS NOT NULL
        AND (p_min_sharpe IS NULL OR (ds.last_backtest_metrics->>'sharpe_ratio')::FLOAT >= p_min_sharpe)
        AND (p_max_drawdown IS NULL OR (ds.last_backtest_metrics->>'max_drawdown')::FLOAT >= p_max_drawdown)
    ORDER BY (ds.last_backtest_metrics->>'sharpe_ratio')::FLOAT DESC NULLS LAST
    LIMIT p_top_n;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 8. 插入示例数据（用于测试）
-- ============================================================

-- 示例: 动量策略配置
INSERT INTO strategy_configs (strategy_type, config, name, description, category, tags, created_by)
VALUES (
    'momentum',
    '{
        "lookback_period": 20,
        "threshold": 0.10,
        "top_n": 20
    }'::jsonb,
    '标准动量策略',
    '选择近期涨幅最大的20只股票',
    'aggressive',
    ARRAY['momentum', 'growth', 'standard'],
    'system'
);

-- 示例: 均值回归策略配置
INSERT INTO strategy_configs (strategy_type, config, name, description, category, tags, created_by)
VALUES (
    'mean_reversion',
    '{
        "lookback_period": 20,
        "std_threshold": 2.0,
        "top_n": 20
    }'::jsonb,
    '标准均值回归策略',
    '选择偏离均值2个标准差的股票',
    'conservative',
    ARRAY['mean_reversion', 'value', 'standard'],
    'system'
);

-- 示例: 多因子策略配置
INSERT INTO strategy_configs (strategy_type, config, name, description, category, tags, created_by)
VALUES (
    'multi_factor',
    '{
        "factors": ["momentum", "value", "quality"],
        "weights": [0.4, 0.3, 0.3],
        "top_n": 30
    }'::jsonb,
    '标准多因子策略',
    '综合动量、价值、质量三个因子',
    'balanced',
    ARRAY['multi_factor', 'balanced', 'standard'],
    'system'
);


-- ============================================================
-- 完成提示
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ Backend适配Core v6.0 - 数据库表创建成功！';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '已创建以下对象:';
    RAISE NOTICE '';
    RAISE NOTICE '📋 表 (3个):';
    RAISE NOTICE '  1. strategy_configs         - 配置驱动策略表';
    RAISE NOTICE '  2. dynamic_strategies       - 动态代码策略表';
    RAISE NOTICE '  3. strategy_executions      - 策略执行记录表';
    RAISE NOTICE '';
    RAISE NOTICE '📊 视图 (2个):';
    RAISE NOTICE '  1. strategy_configs_leaderboard   - 配置策略排行榜';
    RAISE NOTICE '  2. dynamic_strategies_leaderboard - 动态策略排行榜';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ 函数 (2个):';
    RAISE NOTICE '  1. get_top_config_strategies()    - 获取Top配置策略';
    RAISE NOTICE '  2. get_top_dynamic_strategies()   - 获取Top动态策略';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 触发器 (2个):';
    RAISE NOTICE '  1. trigger_strategy_configs_updated_at';
    RAISE NOTICE '  2. trigger_dynamic_strategies_updated_at';
    RAISE NOTICE '';
    RAISE NOTICE '📝 示例数据:';
    RAISE NOTICE '  已插入3个示例策略配置（momentum, mean_reversion, multi_factor）';
    RAISE NOTICE '';
    RAISE NOTICE '下一步:';
    RAISE NOTICE '  - Phase 3: 创建Repository类和Adapter';
    RAISE NOTICE '  - Phase 4: 创建API端点';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
