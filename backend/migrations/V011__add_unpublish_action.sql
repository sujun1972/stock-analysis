-- V011: 添加 unpublish 操作到审核历史表
-- 作者: Backend Team
-- 日期: 2026-03-02
-- 说明: 允许管理员取消已发布的策略

-- 删除旧的约束
ALTER TABLE strategy_publish_reviews
DROP CONSTRAINT strategy_publish_reviews_action_check;

-- 添加新的约束（包含 unpublish）
ALTER TABLE strategy_publish_reviews
ADD CONSTRAINT strategy_publish_reviews_action_check
CHECK (action IN ('approve', 'reject', 'withdraw', 'request_publish', 'unpublish'));
