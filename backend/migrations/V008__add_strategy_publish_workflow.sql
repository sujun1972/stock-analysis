-- V008: Add Strategy Publish Workflow
-- Author: Claude
-- Date: 2026-03-02
-- Description: 添加策略发布审核工作流字段

-- 添加发布状态相关字段到 strategies 表
ALTER TABLE strategies
ADD COLUMN publish_status VARCHAR(20) DEFAULT 'draft'
    CHECK (publish_status IN ('draft', 'pending_review', 'approved', 'rejected')),
ADD COLUMN publish_requested_at TIMESTAMP,
ADD COLUMN publish_reviewed_at TIMESTAMP,
ADD COLUMN publish_reviewed_by INT REFERENCES users(id),
ADD COLUMN publish_reject_reason TEXT;

-- 添加索引以优化查询性能
CREATE INDEX idx_strategies_publish_status ON strategies(publish_status);
CREATE INDEX idx_strategies_publish_reviewed_by ON strategies(publish_reviewed_by);
CREATE INDEX idx_strategies_publish_requested ON strategies(publish_requested_at);

-- 为现有策略设置默认发布状态
-- 系统内置策略（builtin）自动设置为已批准
UPDATE strategies
SET publish_status = 'approved',
    publish_reviewed_at = created_at
WHERE source_type = 'builtin';

-- 已启用的用户策略设置为已批准
UPDATE strategies
SET publish_status = 'approved',
    publish_reviewed_at = updated_at
WHERE source_type IN ('ai', 'custom') AND is_enabled = TRUE;

-- 未启用的用户策略保持草稿状态
-- (已经是默认值 'draft'，无需额外更新)

COMMENT ON COLUMN strategies.publish_status IS '发布状态: draft(草稿), pending_review(待审核), approved(已批准), rejected(已拒绝)';
COMMENT ON COLUMN strategies.publish_requested_at IS '申请发布时间';
COMMENT ON COLUMN strategies.publish_reviewed_at IS '审核完成时间';
COMMENT ON COLUMN strategies.publish_reviewed_by IS '审核人用户ID';
COMMENT ON COLUMN strategies.publish_reject_reason IS '拒绝原因（当 publish_status = rejected 时）';
