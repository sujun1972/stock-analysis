-- V009: Create Strategy Publish Reviews Table
-- Author: Claude
-- Date: 2026-03-02
-- Description: 创建策略发布审核历史记录表

CREATE TABLE strategy_publish_reviews (
    id SERIAL PRIMARY KEY,
    strategy_id INT NOT NULL REFERENCES strategies(id) ON DELETE CASCADE,
    reviewer_id INT NOT NULL REFERENCES users(id),

    -- 审核操作类型
    action VARCHAR(20) NOT NULL CHECK (action IN ('approve', 'reject', 'withdraw')),

    -- 审核前后状态
    previous_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,

    -- 审核意见/拒绝原因
    comment TEXT,

    -- 审核时间
    created_at TIMESTAMP DEFAULT NOW(),

    -- 额外元数据（JSON格式）
    metadata JSONB
);

-- 添加索引优化查询
CREATE INDEX idx_publish_reviews_strategy_id ON strategy_publish_reviews(strategy_id);
CREATE INDEX idx_publish_reviews_reviewer_id ON strategy_publish_reviews(reviewer_id);
CREATE INDEX idx_publish_reviews_action ON strategy_publish_reviews(action);
CREATE INDEX idx_publish_reviews_created_at ON strategy_publish_reviews(created_at DESC);

-- 添加复合索引：按策略ID和时间倒序查询审核历史
CREATE INDEX idx_publish_reviews_strategy_time ON strategy_publish_reviews(strategy_id, created_at DESC);

-- 添加表注释
COMMENT ON TABLE strategy_publish_reviews IS '策略发布审核历史记录表';
COMMENT ON COLUMN strategy_publish_reviews.strategy_id IS '策略ID';
COMMENT ON COLUMN strategy_publish_reviews.reviewer_id IS '审核人/操作人用户ID';
COMMENT ON COLUMN strategy_publish_reviews.action IS '操作类型: approve(批准), reject(拒绝), withdraw(撤回)';
COMMENT ON COLUMN strategy_publish_reviews.previous_status IS '审核前的发布状态';
COMMENT ON COLUMN strategy_publish_reviews.new_status IS '审核后的发布状态';
COMMENT ON COLUMN strategy_publish_reviews.comment IS '审核意见或拒绝原因';
COMMENT ON COLUMN strategy_publish_reviews.metadata IS '额外元数据（JSON格式）';
