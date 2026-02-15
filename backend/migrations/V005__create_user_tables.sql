-- V005: 创建用户管理相关表
-- 用于实现 Admin 用户和 Frontend 用户的认证、权限和配额管理

-- ============================================================
-- 1. 用户基础表
-- ============================================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'super_admin', 'admin', 'vip_user', 'normal_user', 'trial_user'
    is_active BOOLEAN DEFAULT true,
    is_email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    login_count INTEGER DEFAULT 0,

    -- 用户资料
    full_name VARCHAR(100),
    avatar_url VARCHAR(500),
    phone VARCHAR(20),

    -- 约束
    CONSTRAINT chk_role CHECK (role IN ('super_admin', 'admin', 'vip_user', 'normal_user', 'trial_user'))
);

-- 用户表索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);

-- ============================================================
-- 2. 用户配额表（针对普通用户的使用限制）
-- ============================================================
CREATE TABLE user_quotas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    -- 回测配额
    backtest_quota_total INTEGER DEFAULT 10,      -- 总配额
    backtest_quota_used INTEGER DEFAULT 0,         -- 已使用
    backtest_quota_reset_at TIMESTAMPTZ,           -- 配额重置时间（每月）

    -- ML预测配额
    ml_prediction_quota_total INTEGER DEFAULT 5,
    ml_prediction_quota_used INTEGER DEFAULT 0,
    ml_prediction_quota_reset_at TIMESTAMPTZ,

    -- 策略数量限制
    max_strategies INTEGER DEFAULT 3,              -- 最多创建策略数
    current_strategies INTEGER DEFAULT 0,          -- 当前策略数

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 配额表索引
CREATE INDEX idx_user_quotas_user_id ON user_quotas(user_id);

-- ============================================================
-- 3. 登录历史表
-- ============================================================
CREATE TABLE login_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    login_at TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    login_successful BOOLEAN DEFAULT true,
    failure_reason VARCHAR(200)
);

-- 登录历史索引
CREATE INDEX idx_login_history_user_id ON login_history(user_id);
CREATE INDEX idx_login_history_login_at ON login_history(login_at DESC);
CREATE INDEX idx_login_history_successful ON login_history(login_successful);

-- ============================================================
-- 4. 用户操作日志表（管理员操作审计）
-- ============================================================
CREATE TABLE user_activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,  -- 'create_strategy', 'run_backtest', 'delete_experiment' 等
    resource_type VARCHAR(50),          -- 'strategy', 'backtest', 'experiment' 等
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 操作日志索引
CREATE INDEX idx_activity_logs_user_id ON user_activity_logs(user_id);
CREATE INDEX idx_activity_logs_created_at ON user_activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_action_type ON user_activity_logs(action_type);
CREATE INDEX idx_activity_logs_resource ON user_activity_logs(resource_type, resource_id);

-- ============================================================
-- 5. 刷新令牌表（JWT Token管理）
-- ============================================================
CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    is_revoked BOOLEAN DEFAULT false
);

-- 令牌表索引
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_is_revoked ON refresh_tokens(is_revoked);

-- ============================================================
-- 6. 触发器：自动更新 updated_at 字段
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_quotas_updated_at
    BEFORE UPDATE ON user_quotas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 7. 触发器：创建用户时自动创建配额记录
-- ============================================================
CREATE OR REPLACE FUNCTION create_user_quota_on_user_insert()
RETURNS TRIGGER AS $$
DECLARE
    quota_total INTEGER;
    ml_quota_total INTEGER;
    max_strat INTEGER;
BEGIN
    -- 根据角色设置配额
    IF NEW.role = 'super_admin' OR NEW.role = 'admin' THEN
        quota_total := 999999;  -- 无限制
        ml_quota_total := 999999;
        max_strat := 999999;
    ELSIF NEW.role = 'vip_user' THEN
        quota_total := 999999;  -- VIP无限制
        ml_quota_total := 999999;
        max_strat := 999999;
    ELSIF NEW.role = 'normal_user' THEN
        quota_total := 10;
        ml_quota_total := 5;
        max_strat := 10;
    ELSIF NEW.role = 'trial_user' THEN
        quota_total := 5;
        ml_quota_total := 2;
        max_strat := 3;
    END IF;

    INSERT INTO user_quotas (
        user_id,
        backtest_quota_total,
        backtest_quota_used,
        backtest_quota_reset_at,
        ml_prediction_quota_total,
        ml_prediction_quota_used,
        ml_prediction_quota_reset_at,
        max_strategies,
        current_strategies
    ) VALUES (
        NEW.id,
        quota_total,
        0,
        NOW() + INTERVAL '1 month',
        ml_quota_total,
        0,
        NOW() + INTERVAL '1 month',
        max_strat,
        0
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_user_quota
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_user_quota_on_user_insert();

-- ============================================================
-- 8. 视图：用户完整信息（包含配额）
-- ============================================================
CREATE VIEW user_full_info AS
SELECT
    u.id,
    u.username,
    u.email,
    u.role,
    u.is_active,
    u.is_email_verified,
    u.created_at,
    u.updated_at,
    u.last_login_at,
    u.login_count,
    u.full_name,
    u.avatar_url,
    u.phone,
    q.backtest_quota_total,
    q.backtest_quota_used,
    q.backtest_quota_total - q.backtest_quota_used AS backtest_quota_remaining,
    q.backtest_quota_reset_at,
    q.ml_prediction_quota_total,
    q.ml_prediction_quota_used,
    q.ml_prediction_quota_total - q.ml_prediction_quota_used AS ml_quota_remaining,
    q.ml_prediction_quota_reset_at,
    q.max_strategies,
    q.current_strategies,
    q.max_strategies - q.current_strategies AS strategies_remaining
FROM users u
LEFT JOIN user_quotas q ON u.id = q.user_id;

-- ============================================================
-- 9. 函数：检查和重置配额
-- ============================================================
CREATE OR REPLACE FUNCTION reset_quota_if_needed(p_user_id INTEGER)
RETURNS void AS $$
BEGIN
    -- 检查回测配额是否需要重置
    UPDATE user_quotas
    SET
        backtest_quota_used = 0,
        backtest_quota_reset_at = NOW() + INTERVAL '1 month'
    WHERE user_id = p_user_id
    AND backtest_quota_reset_at < NOW();

    -- 检查ML预测配额是否需要重置
    UPDATE user_quotas
    SET
        ml_prediction_quota_used = 0,
        ml_prediction_quota_reset_at = NOW() + INTERVAL '1 month'
    WHERE user_id = p_user_id
    AND ml_prediction_quota_reset_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 10. 函数：增加配额使用次数
-- ============================================================
CREATE OR REPLACE FUNCTION increment_quota_usage(
    p_user_id INTEGER,
    p_quota_type VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_remaining INTEGER;
BEGIN
    -- 先重置过期的配额
    PERFORM reset_quota_if_needed(p_user_id);

    -- 根据类型增加使用次数
    IF p_quota_type = 'backtest' THEN
        UPDATE user_quotas
        SET backtest_quota_used = backtest_quota_used + 1
        WHERE user_id = p_user_id
        AND backtest_quota_used < backtest_quota_total
        RETURNING (backtest_quota_total - backtest_quota_used) INTO v_remaining;
    ELSIF p_quota_type = 'ml_prediction' THEN
        UPDATE user_quotas
        SET ml_prediction_quota_used = ml_prediction_quota_used + 1
        WHERE user_id = p_user_id
        AND ml_prediction_quota_used < ml_prediction_quota_total
        RETURNING (ml_prediction_quota_total - ml_prediction_quota_used) INTO v_remaining;
    ELSE
        RETURN false;
    END IF;

    -- 如果更新成功，返回true
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 11. 注释
-- ============================================================
COMMENT ON TABLE users IS '用户基础表，存储Admin和Frontend用户';
COMMENT ON TABLE user_quotas IS '用户配额表，限制普通用户的使用次数';
COMMENT ON TABLE login_history IS '登录历史记录表，用于安全审计';
COMMENT ON TABLE user_activity_logs IS '用户操作日志表，记录所有重要操作';
COMMENT ON TABLE refresh_tokens IS 'JWT刷新令牌表，用于Token管理';
COMMENT ON VIEW user_full_info IS '用户完整信息视图，包含配额计算';
