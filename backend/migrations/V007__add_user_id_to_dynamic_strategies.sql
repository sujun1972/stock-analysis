-- ============================================================
-- 迁移脚本: V007 - 为 dynamic_strategies 表添加 user_id 外键
-- 版本: 1.0.0
-- 创建日期: 2026-03-09
-- 说明: 添加 user_id 外键字段，关联用户表，以实现策略与用户的绑定
-- ============================================================

-- 1. 添加 user_id 列（允许 NULL，因为已有数据可能没有用户信息）
ALTER TABLE dynamic_strategies
ADD COLUMN IF NOT EXISTS user_id INT;

-- 2. 添加外键约束（级联删除：用户删除时，其策略也删除）
ALTER TABLE dynamic_strategies
ADD CONSTRAINT fk_dynamic_strategies_user
FOREIGN KEY (user_id)
REFERENCES users(id)
ON DELETE CASCADE;

-- 3. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_dynamic_strategies_user_id
ON dynamic_strategies(user_id);

-- 4. 创建复合索引：user_id + is_enabled（常用查询组合）
CREATE INDEX IF NOT EXISTS idx_dynamic_strategies_user_enabled
ON dynamic_strategies(user_id, is_enabled)
WHERE user_id IS NOT NULL;

-- 5. 添加注释
COMMENT ON COLUMN dynamic_strategies.user_id IS '策略所属用户ID（NULL表示系统策略或未关联用户）';

-- ============================================================
-- 数据迁移说明：
-- - 已有的策略 user_id 为 NULL
-- - 新创建的策略会自动填充 user_id
-- - 管理员可以通过 Admin 项目手动绑定已有策略的用户
-- ============================================================
