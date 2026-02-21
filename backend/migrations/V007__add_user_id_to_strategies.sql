-- ============================================================
-- 为strategies表添加用户关联
-- 创建时间: 2026-02-21
-- 说明: 添加user_id字段，支持用户拥有自己的策略
-- ============================================================

-- 1. 添加user_id列
ALTER TABLE strategies
    ADD COLUMN IF NOT EXISTS user_id INT REFERENCES users(id) ON DELETE CASCADE;

-- 2. 更新strategy_type列的类型和约束
ALTER TABLE strategies
    ALTER COLUMN strategy_type TYPE VARCHAR(20);

-- 3. 删除旧的唯一约束（如果存在）
ALTER TABLE strategies DROP CONSTRAINT IF EXISTS strategies_name_key;

-- 4. 添加新的唯一约束：用户策略的name在该用户下唯一，系统策略在全局唯一
ALTER TABLE strategies
    ADD CONSTRAINT unique_user_strategy_name UNIQUE (user_id, name);

-- 5. 为user_id添加索引
CREATE INDEX IF NOT EXISTS idx_strategies_user_id ON strategies(user_id);
CREATE INDEX IF NOT EXISTS idx_strategies_user_enabled ON strategies(user_id, is_enabled) WHERE user_id IS NOT NULL;

-- 6. 更新strategy_type的CHECK约束
ALTER TABLE strategies DROP CONSTRAINT IF EXISTS valid_strategy_type;
ALTER TABLE strategies DROP CONSTRAINT IF EXISTS chk_strategy_type;
ALTER TABLE strategies
    ADD CONSTRAINT valid_strategy_type CHECK (
        strategy_type IN ('stock_selection', 'entry', 'exit')
    );

-- 7. 创建视图：用户策略汇总
DROP VIEW IF EXISTS user_strategies_summary CASCADE;
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

-- 8. 创建函数：获取用户的策略列表
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

-- 9. 确保触发器函数存在并正确
DROP FUNCTION IF EXISTS update_user_strategy_count() CASCADE;
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

-- 10. 移除旧的触发器并创建新的
DROP TRIGGER IF EXISTS trigger_update_user_strategy_count ON strategies;
CREATE TRIGGER trigger_update_user_strategy_count
    AFTER INSERT OR UPDATE OR DELETE ON strategies
    FOR EACH ROW
    EXECUTE FUNCTION update_user_strategy_count();

-- 11. 插入系统内置策略示例数据（如果不存在）
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
) ON CONFLICT (user_id, name) DO NOTHING;

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
) ON CONFLICT (user_id, name) DO NOTHING;

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
) ON CONFLICT (user_id, name) DO NOTHING;

-- ============================================================
-- 完成提示
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ strategies表用户关联添加成功！';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '已完成:';
    RAISE NOTICE '  ✓ 添加user_id列';
    RAISE NOTICE '  ✓ 更新strategy_type支持三种类型（stock_selection, entry, exit）';
    RAISE NOTICE '  ✓ 添加唯一约束和索引';
    RAISE NOTICE '  ✓ 创建用户策略汇总视图';
    RAISE NOTICE '  ✓ 创建用户策略查询函数';
    RAISE NOTICE '  ✓ 添加用户策略计数触发器';
    RAISE NOTICE '  ✓ 插入3个系统内置策略示例';
    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
