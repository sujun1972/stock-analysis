-- ============================================================
-- 统一策略表和用户关联
-- 创建时间: 2026-02-21
-- 说明: 创建统一的strategies表，支持用户关联和三种策略类型（选股、入场、离场）
-- ============================================================

-- ============================================================
-- 1. 创建统一策略表
-- ============================================================
CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,

    -- 用户关联
    user_id INT REFERENCES users(id) ON DELETE CASCADE,  -- 策略所属用户（NULL表示系统策略）

    -- 基本信息
    name VARCHAR(200) NOT NULL,                          -- 策略唯一标识
    display_name VARCHAR(200) NOT NULL,                  -- 显示名称
    class_name VARCHAR(100) NOT NULL,                    -- Python类名

    -- 核心代码
    code TEXT NOT NULL,                                  -- 完整的 Python 策略代码
    code_hash VARCHAR(64) NOT NULL,                      -- SHA256 校验值

    -- 来源分类
    source_type VARCHAR(20) NOT NULL,                    -- builtin (系统内置), ai (AI生成), custom (用户自定义)

    -- 策略类型：区分选股策略、入场策略和离场策略
    strategy_type VARCHAR(20) NOT NULL DEFAULT 'stock_selection',
    -- stock_selection (选股策略), entry (入场策略), exit (离场策略)

    -- 策略元信息
    description TEXT,                                    -- 策略说明
    category VARCHAR(50),                                -- 类别
    tags VARCHAR(100)[],                                 -- 标签数组

    -- 默认参数
    default_params JSONB,                                -- 默认参数 JSON

    -- 状态和验证
    validation_status VARCHAR(20) DEFAULT 'pending',     -- pending, passed, failed, validating
    validation_errors JSONB,                             -- 验证错误详情
    validation_warnings JSONB,                           -- 验证警告
    risk_level VARCHAR(20) DEFAULT 'medium',             -- safe, low, medium, high
    is_enabled BOOLEAN DEFAULT TRUE,                     -- 是否启用

    -- 使用统计
    usage_count INT DEFAULT 0,                           -- 使用次数
    backtest_count INT DEFAULT 0,                        -- 回测次数
    avg_sharpe_ratio DECIMAL(10, 4),                     -- 平均夏普率
    avg_annual_return DECIMAL(10, 4),                    -- 平均年化收益

    -- 版本和审计
    version INT DEFAULT 1,                               -- 版本号
    parent_strategy_id INT REFERENCES strategies(id),    -- 父策略ID
    created_by VARCHAR(100),                             -- 创建人
    created_at TIMESTAMP DEFAULT NOW(),                  -- 创建时间
    updated_at TIMESTAMP DEFAULT NOW(),                  -- 更新时间
    last_used_at TIMESTAMP,                              -- 最后使用时间

    -- 约束
    CONSTRAINT valid_source_type CHECK (
        source_type IN ('builtin', 'ai', 'custom')
    ),
    CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN ('stock_selection', 'entry', 'exit')
    ),
    CONSTRAINT valid_validation_status CHECK (
        validation_status IN ('pending', 'passed', 'failed', 'validating')
    ),
    CONSTRAINT valid_risk_level CHECK (
        risk_level IN ('safe', 'low', 'medium', 'high')
    ),
    -- 确保用户策略的name在该用户下唯一，系统策略在全局唯一
    CONSTRAINT unique_user_strategy_name UNIQUE (user_id, name)
);

-- 为策略表创建索引
CREATE INDEX idx_strategies_user_id ON strategies(user_id);
CREATE INDEX idx_strategies_name ON strategies(name);
CREATE INDEX idx_strategies_source_type ON strategies(source_type);
CREATE INDEX idx_strategies_strategy_type ON strategies(strategy_type);
CREATE INDEX idx_strategies_enabled ON strategies(is_enabled);
CREATE INDEX idx_strategies_validation ON strategies(validation_status);
CREATE INDEX idx_strategies_created ON strategies(created_at DESC);
CREATE INDEX idx_strategies_tags ON strategies USING GIN(tags);
CREATE INDEX idx_strategies_user_enabled ON strategies(user_id, is_enabled) WHERE user_id IS NOT NULL;

-- 添加触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_strategies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_strategies_updated_at
    BEFORE UPDATE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_strategies_updated_at();


-- ============================================================
-- 2. 更新策略执行表以支持统一的strategies表
-- ============================================================
ALTER TABLE strategy_executions
    ADD COLUMN IF NOT EXISTS strategy_id INT REFERENCES strategies(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_exec_strategy_id ON strategy_executions(strategy_id, created_at DESC);

-- 更新约束，允许使用新的strategy_id
ALTER TABLE strategy_executions DROP CONSTRAINT IF EXISTS at_least_one_strategy;
ALTER TABLE strategy_executions ADD CONSTRAINT at_least_one_strategy CHECK (
    (predefined_strategy_type IS NOT NULL)::int +
    (config_strategy_id IS NOT NULL)::int +
    (dynamic_strategy_id IS NOT NULL)::int +
    (strategy_id IS NOT NULL)::int >= 1
);


-- ============================================================
-- 3. 插入系统内置策略示例数据
-- ============================================================

-- 示例: 动量选股策略（股票筛选策略）
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, created_by
) VALUES (
    NULL,  -- 系统策略
    'momentum_stock_selection',
    '动量选股策略',
    'MomentumStockSelectionStrategy',
    '# Placeholder code for momentum stock selection strategy
class MomentumStockSelectionStrategy:
    def select_stocks(self, universe, lookback_period=20, top_n=50):
        """选择动量最强的股票"""
        pass
',
    encode(sha256('placeholder_momentum_code'::bytea), 'hex'),
    'builtin',
    'stock_selection',
    '基于过去N日涨幅选择动量最强的股票',
    'momentum',
    ARRAY['动量', '趋势', '选股'],
    '{"lookback_period": 20, "top_n": 50}'::jsonb,
    'passed',
    'low',
    'system'
);

-- 示例: RSI入场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, created_by
) VALUES (
    NULL,
    'rsi_entry_strategy',
    'RSI入场策略',
    'RSIEntryStrategy',
    '# Placeholder code for RSI entry strategy
class RSIEntryStrategy:
    def should_enter(self, stock, rsi_period=14, oversold_threshold=30):
        """RSI超卖时入场"""
        pass
',
    encode(sha256('placeholder_rsi_entry_code'::bytea), 'hex'),
    'builtin',
    'entry',
    '当RSI指标低于超卖阈值时入场',
    'reversal',
    ARRAY['RSI', '反转', '入场'],
    '{"rsi_period": 14, "oversold_threshold": 30}'::jsonb,
    'passed',
    'medium',
    'system'
);

-- 示例: 止损离场策略
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, created_by
) VALUES (
    NULL,
    'stop_loss_exit_strategy',
    '止损离场策略',
    'StopLossExitStrategy',
    '# Placeholder code for stop loss exit strategy
class StopLossExitStrategy:
    def should_exit(self, current_price, entry_price, stop_loss_pct=0.05):
        """价格下跌超过止损百分比时离场"""
        pass
',
    encode(sha256('placeholder_stop_loss_code'::bytea), 'hex'),
    'builtin',
    'exit',
    '当价格下跌超过指定百分比时止损离场',
    'risk_management',
    ARRAY['止损', '风险管理', '离场'],
    '{"stop_loss_pct": 0.05}'::jsonb,
    'passed',
    'safe',
    'system'
);


-- ============================================================
-- 4. 创建视图：用户策略汇总
-- ============================================================
CREATE OR REPLACE VIEW user_strategies_summary AS
SELECT
    u.id AS user_id,
    u.username,
    u.email,
    COUNT(s.id) AS total_strategies,
    COUNT(s.id) FILTER (WHERE s.strategy_type = 'stock_selection') AS stock_selection_count,
    COUNT(s.id) FILTER (WHERE s.strategy_type = 'entry') AS entry_count,
    COUNT(s.id) FILTER (WHERE s.strategy_type = 'exit') AS exit_count,
    COUNT(s.id) FILTER (WHERE s.is_enabled = TRUE) AS enabled_count,
    COUNT(s.id) FILTER (WHERE s.validation_status = 'passed') AS validated_count,
    MAX(s.created_at) AS last_strategy_created_at
FROM users u
LEFT JOIN strategies s ON u.id = s.user_id
GROUP BY u.id, u.username, u.email;


-- ============================================================
-- 5. 创建函数：获取用户的策略列表
-- ============================================================
CREATE OR REPLACE FUNCTION get_user_strategies(
    p_user_id INT,
    p_strategy_type VARCHAR DEFAULT NULL,
    p_is_enabled BOOLEAN DEFAULT NULL
)
RETURNS TABLE (
    strategy_id INT,
    strategy_name VARCHAR,
    display_name VARCHAR,
    strategy_type VARCHAR,
    description TEXT,
    is_enabled BOOLEAN,
    validation_status VARCHAR,
    created_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.name,
        s.display_name,
        s.strategy_type,
        s.description,
        s.is_enabled,
        s.validation_status,
        s.created_at
    FROM strategies s
    WHERE
        s.user_id = p_user_id
        AND (p_strategy_type IS NULL OR s.strategy_type = p_strategy_type)
        AND (p_is_enabled IS NULL OR s.is_enabled = p_is_enabled)
    ORDER BY s.created_at DESC;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 6. 更新用户配额表，添加策略数量统计触发器
-- ============================================================
CREATE OR REPLACE FUNCTION update_user_strategy_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.user_id IS NOT NULL THEN
        -- 插入策略时增加计数
        UPDATE user_quotas
        SET current_strategies = current_strategies + 1
        WHERE user_id = NEW.user_id;
    ELSIF TG_OP = 'DELETE' AND OLD.user_id IS NOT NULL THEN
        -- 删除策略时减少计数
        UPDATE user_quotas
        SET current_strategies = GREATEST(0, current_strategies - 1)
        WHERE user_id = OLD.user_id;
    ELSIF TG_OP = 'UPDATE' AND OLD.user_id IS DISTINCT FROM NEW.user_id THEN
        -- 策略转移到其他用户（边缘情况）
        IF OLD.user_id IS NOT NULL THEN
            UPDATE user_quotas
            SET current_strategies = GREATEST(0, current_strategies - 1)
            WHERE user_id = OLD.user_id;
        END IF;
        IF NEW.user_id IS NOT NULL THEN
            UPDATE user_quotas
            SET current_strategies = current_strategies + 1
            WHERE user_id = NEW.user_id;
        END IF;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_user_strategy_count
    AFTER INSERT OR UPDATE OR DELETE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_user_strategy_count();


-- ============================================================
-- 完成提示
-- ============================================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ 统一策略表创建成功！';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '已创建以下对象:';
    RAISE NOTICE '';
    RAISE NOTICE '📋 表 (1个):';
    RAISE NOTICE '  1. strategies - 统一策略表（支持用户关联）';
    RAISE NOTICE '';
    RAISE NOTICE '📊 视图 (1个):';
    RAISE NOTICE '  1. user_strategies_summary - 用户策略汇总视图';
    RAISE NOTICE '';
    RAISE NOTICE '⚡ 函数 (1个):';
    RAISE NOTICE '  1. get_user_strategies() - 获取用户策略列表';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 触发器 (2个):';
    RAISE NOTICE '  1. trigger_strategies_updated_at - 自动更新时间戳';
    RAISE NOTICE '  2. trigger_update_user_strategy_count - 自动更新用户策略计数';
    RAISE NOTICE '';
    RAISE NOTICE '📝 示例数据:';
    RAISE NOTICE '  已插入3个系统内置策略示例';
    RAISE NOTICE '';
    RAISE NOTICE '策略类型:';
    RAISE NOTICE '  - stock_selection: 选股策略';
    RAISE NOTICE '  - entry: 入场策略';
    RAISE NOTICE '  - exit: 离场策略';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
