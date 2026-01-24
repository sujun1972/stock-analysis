-- ============================================================
-- 自动化实验系统数据库表
-- 创建时间: 2024-01-24
-- 说明: 支持批量模型训练、回测和自动筛选
-- ============================================================

-- 1. 实验批次表
-- 用于管理一组相关的实验（如参数网格搜索）
CREATE TABLE IF NOT EXISTS experiment_batches (
    id SERIAL PRIMARY KEY,

    -- 基本信息
    batch_name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,

    -- 实验策略
    strategy VARCHAR(20) NOT NULL DEFAULT 'grid',  -- grid, random, bayesian
    param_space JSONB NOT NULL,  -- 参数空间定义

    -- 统计信息
    total_experiments INT DEFAULT 0,
    completed_experiments INT DEFAULT 0,
    failed_experiments INT DEFAULT 0,
    running_experiments INT DEFAULT 0,

    -- 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, paused, completed, failed

    -- 配置
    config JSONB,  -- 批次级别配置（如并行度、回测设置等）

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- 元数据
    created_by VARCHAR(100),
    tags VARCHAR(255)[],  -- 标签数组，便于分类

    -- 索引
    CONSTRAINT valid_strategy CHECK (strategy IN ('grid', 'random', 'bayesian'))
);

-- 为批次表创建索引
CREATE INDEX idx_batch_status ON experiment_batches(status);
CREATE INDEX idx_batch_created_at ON experiment_batches(created_at DESC);
CREATE INDEX idx_batch_tags ON experiment_batches USING GIN(tags);


-- 2. 实验记录表
-- 存储每个单独实验的详细信息
CREATE TABLE IF NOT EXISTS experiments (
    id SERIAL PRIMARY KEY,

    -- 关联批次
    batch_id INT REFERENCES experiment_batches(id) ON DELETE CASCADE,

    -- 实验标识
    experiment_name VARCHAR(200) NOT NULL,
    experiment_hash VARCHAR(64) UNIQUE,  -- 配置的MD5哈希，避免重复实验

    -- 训练配置
    config JSONB NOT NULL,  -- 完整的训练参数

    -- 训练结果
    model_id VARCHAR(100),  -- 训练完成后的模型ID
    model_path VARCHAR(500),  -- 模型文件路径
    train_metrics JSONB,  -- 训练指标 {rmse, r2, ic, rank_ic, ...}
    feature_importance JSONB,  -- 特征重要性

    -- 回测结果
    backtest_status VARCHAR(20),  -- pending, running, completed, failed, skipped
    backtest_metrics JSONB,  -- 回测指标 {annual_return, sharpe, max_drawdown, ...}
    backtest_trades JSONB,  -- 交易明细（可选，大数据量时可单独存储）

    -- 综合评分
    rank_score FLOAT,  -- 综合评分（用于排序）
    rank_position INT,  -- 在批次内的排名

    -- 状态和错误
    status VARCHAR(20) DEFAULT 'pending',  -- pending, training, backtesting, completed, failed
    error_message TEXT,
    retry_count INT DEFAULT 0,

    -- 资源消耗
    train_duration_seconds INT,
    backtest_duration_seconds INT,
    total_duration_seconds INT,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    train_started_at TIMESTAMP,
    train_completed_at TIMESTAMP,
    backtest_started_at TIMESTAMP,
    backtest_completed_at TIMESTAMP,

    -- 元数据
    notes TEXT,

    -- 约束
    CONSTRAINT valid_experiment_status CHECK (status IN ('pending', 'training', 'backtesting', 'completed', 'failed', 'skipped')),
    CONSTRAINT valid_backtest_status CHECK (backtest_status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

-- 为实验表创建索引
CREATE INDEX idx_exp_batch_id ON experiments(batch_id);
CREATE INDEX idx_exp_status ON experiments(status);
CREATE INDEX idx_exp_rank_score ON experiments(rank_score DESC NULLS LAST);
CREATE INDEX idx_exp_model_id ON experiments(model_id);
CREATE INDEX idx_exp_config ON experiments USING GIN(config);  -- 支持JSONB查询


-- 3. 参数重要性分析表
-- 用于分析哪些参数对模型性能影响最大
CREATE TABLE IF NOT EXISTS parameter_importance (
    id SERIAL PRIMARY KEY,
    batch_id INT REFERENCES experiment_batches(id) ON DELETE CASCADE,

    -- 参数信息
    parameter_name VARCHAR(100) NOT NULL,
    parameter_type VARCHAR(50),  -- model, feature, data, hyperparameter

    -- 重要性指标
    importance_score FLOAT,  -- 重要性评分（0-1）
    correlation_with_performance FLOAT,  -- 与性能的相关系数

    -- 统计信息
    num_experiments INT,  -- 涉及该参数的实验数量
    value_distribution JSONB,  -- 参数值分布

    -- 时间戳
    computed_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(batch_id, parameter_name)
);

CREATE INDEX idx_param_importance ON parameter_importance(batch_id, importance_score DESC);


-- 4. 实验日志表
-- 记录实验过程中的详细日志（可选，用于调试）
CREATE TABLE IF NOT EXISTS experiment_logs (
    id BIGSERIAL PRIMARY KEY,
    experiment_id INT REFERENCES experiments(id) ON DELETE CASCADE,

    -- 日志信息
    log_level VARCHAR(20),  -- DEBUG, INFO, WARNING, ERROR
    log_message TEXT NOT NULL,
    log_data JSONB,  -- 结构化日志数据

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW()
);

-- 为日志表创建索引（支持按实验和时间查询）
CREATE INDEX idx_log_experiment_id ON experiment_logs(experiment_id, created_at DESC);
CREATE INDEX idx_log_level ON experiment_logs(log_level);


-- 5. 模型性能对比视图
-- 便于查询和对比不同模型的性能
CREATE OR REPLACE VIEW model_performance_comparison AS
SELECT
    e.id,
    e.batch_id,
    eb.batch_name,
    e.experiment_name,
    e.model_id,

    -- 训练指标
    e.train_metrics->>'rmse' AS train_rmse,
    e.train_metrics->>'r2' AS train_r2,
    e.train_metrics->>'ic' AS train_ic,
    e.train_metrics->>'rank_ic' AS train_rank_ic,

    -- 回测指标
    e.backtest_metrics->>'annual_return' AS annual_return,
    e.backtest_metrics->>'sharpe_ratio' AS sharpe_ratio,
    e.backtest_metrics->>'max_drawdown' AS max_drawdown,
    e.backtest_metrics->>'win_rate' AS win_rate,
    e.backtest_metrics->>'profit_factor' AS profit_factor,

    -- 综合评分
    e.rank_score,
    e.rank_position,

    -- 配置
    e.config->>'symbol' AS symbol,
    e.config->>'model_type' AS model_type,
    e.config->>'target_period' AS target_period,

    -- 状态
    e.status,
    e.created_at
FROM experiments e
JOIN experiment_batches eb ON e.batch_id = eb.id
WHERE e.status = 'completed'
ORDER BY e.rank_score DESC NULLS LAST;


-- 6. 批次统计视图
-- 快速查看批次的整体统计信息
CREATE OR REPLACE VIEW batch_statistics AS
SELECT
    eb.id AS batch_id,
    eb.batch_name,
    eb.strategy,
    eb.status,
    eb.total_experiments,
    eb.completed_experiments,
    eb.failed_experiments,
    eb.running_experiments,

    -- 成功率
    CASE
        WHEN eb.total_experiments > 0
        THEN ROUND((eb.completed_experiments::FLOAT / eb.total_experiments * 100)::NUMERIC, 2)
        ELSE 0
    END AS success_rate_pct,

    -- 时间统计
    eb.created_at,
    eb.started_at,
    eb.completed_at,
    EXTRACT(EPOCH FROM (COALESCE(eb.completed_at, NOW()) - eb.started_at)) / 3600 AS duration_hours,

    -- 性能统计
    (SELECT AVG((e.rank_score)::FLOAT)
     FROM experiments e
     WHERE e.batch_id = eb.id AND e.status = 'completed') AS avg_rank_score,

    (SELECT MAX((e.rank_score)::FLOAT)
     FROM experiments e
     WHERE e.batch_id = eb.id AND e.status = 'completed') AS max_rank_score,

    -- Top模型
    (SELECT e.model_id
     FROM experiments e
     WHERE e.batch_id = eb.id AND e.status = 'completed'
     ORDER BY e.rank_score DESC NULLS LAST
     LIMIT 1) AS top_model_id

FROM experiment_batches eb;


-- 7. 创建用于快速查询Top模型的函数
CREATE OR REPLACE FUNCTION get_top_models(
    p_batch_id INT,
    p_top_n INT DEFAULT 10,
    p_min_sharpe FLOAT DEFAULT NULL,
    p_max_drawdown FLOAT DEFAULT NULL,
    p_min_annual_return FLOAT DEFAULT NULL
)
RETURNS TABLE (
    experiment_id INT,
    model_id VARCHAR,
    rank_score FLOAT,
    annual_return FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown FLOAT,
    config JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.model_id,
        e.rank_score,
        (e.backtest_metrics->>'annual_return')::FLOAT,
        (e.backtest_metrics->>'sharpe_ratio')::FLOAT,
        (e.backtest_metrics->>'max_drawdown')::FLOAT,
        e.config
    FROM experiments e
    WHERE
        e.batch_id = p_batch_id
        AND e.status = 'completed'
        AND e.backtest_status = 'completed'
        AND (p_min_sharpe IS NULL OR (e.backtest_metrics->>'sharpe_ratio')::FLOAT >= p_min_sharpe)
        AND (p_max_drawdown IS NULL OR (e.backtest_metrics->>'max_drawdown')::FLOAT >= p_max_drawdown)
        AND (p_min_annual_return IS NULL OR (e.backtest_metrics->>'annual_return')::FLOAT >= p_min_annual_return)
    ORDER BY e.rank_score DESC NULLS LAST
    LIMIT p_top_n;
END;
$$ LANGUAGE plpgsql;


-- 8. 插入示例数据（可选，用于测试）
-- INSERT INTO experiment_batches (batch_name, description, strategy, param_space)
-- VALUES (
--     '测试批次_Grid搜索',
--     '测试网格搜索功能',
--     'grid',
--     '{"symbols": ["000001", "600000"], "model_types": ["lightgbm", "gru"]}'::jsonb
-- );


-- ============================================================
-- 权限设置（根据实际情况调整）
-- ============================================================

-- 如果有特定的数据库用户，授予权限
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO your_app_user;


-- ============================================================
-- 完成提示
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '✅ 实验系统数据库表创建成功！';
    RAISE NOTICE '已创建以下对象:';
    RAISE NOTICE '  - 表: experiment_batches, experiments, parameter_importance, experiment_logs';
    RAISE NOTICE '  - 视图: model_performance_comparison, batch_statistics';
    RAISE NOTICE '  - 函数: get_top_models()';
    RAISE NOTICE '';
    RAISE NOTICE '下一步: 运行后端服务并测试API';
END $$;
