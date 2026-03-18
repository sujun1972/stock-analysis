-- 创建通用的Celery任务执行历史表
-- 用于记录所有类型的异步任务执行历史

CREATE TABLE IF NOT EXISTS celery_task_history (
    id SERIAL PRIMARY KEY,

    -- 任务标识
    celery_task_id VARCHAR(255) NOT NULL UNIQUE,  -- Celery任务ID (UUID)
    task_name VARCHAR(255) NOT NULL,              -- Celery任务名称
    display_name VARCHAR(255),                     -- 用户友好的显示名称
    task_type VARCHAR(50),                         -- 任务类型: sync, sentiment, ai_analysis, backtest, premarket, scheduler, other

    -- 用户信息
    user_id INTEGER,                               -- 执行任务的用户ID

    -- 任务状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, running, success, failure, progress
    progress INTEGER DEFAULT 0,                    -- 进度 0-100

    -- 时间信息
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 任务创建时间
    started_at TIMESTAMP,                          -- 任务开始执行时间
    completed_at TIMESTAMP,                        -- 任务完成时间
    duration_ms INTEGER,                           -- 执行耗时（毫秒）

    -- 结果信息
    result JSONB,                                  -- 任务执行结果
    error TEXT,                                    -- 错误信息

    -- Worker信息
    worker VARCHAR(255),                           -- 执行任务的Worker

    -- 任务参数
    params JSONB,                                  -- 任务参数

    -- 元数据
    metadata JSONB,                                -- 其他元数据

    CONSTRAINT fk_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
);

-- 创建索引以提高查询性能
CREATE INDEX idx_celery_task_history_celery_task_id ON celery_task_history(celery_task_id);
CREATE INDEX idx_celery_task_history_user_id ON celery_task_history(user_id);
CREATE INDEX idx_celery_task_history_task_type ON celery_task_history(task_type);
CREATE INDEX idx_celery_task_history_status ON celery_task_history(status);
CREATE INDEX idx_celery_task_history_created_at ON celery_task_history(created_at DESC);
CREATE INDEX idx_celery_task_history_completed_at ON celery_task_history(completed_at DESC);

-- 添加注释
COMMENT ON TABLE celery_task_history IS '通用Celery任务执行历史表，记录所有异步任务的执行情况';
COMMENT ON COLUMN celery_task_history.celery_task_id IS 'Celery任务ID（UUID格式）';
COMMENT ON COLUMN celery_task_history.task_name IS 'Celery任务名称（如: tasks.sync_moneyflow_hsgt）';
COMMENT ON COLUMN celery_task_history.display_name IS '用户友好的任务名称（如: 沪深港通资金流向）';
COMMENT ON COLUMN celery_task_history.task_type IS '任务类型分类';
COMMENT ON COLUMN celery_task_history.status IS '任务状态: pending, running, success, failure, progress';
COMMENT ON COLUMN celery_task_history.duration_ms IS '任务执行耗时（毫秒）';
