-- Migration: 004_download_checkpoints
-- Description: 创建下载断点续传相关表
-- Date: 2026-01-30

-- ============================================================
-- 下载检查点表
-- ============================================================
CREATE TABLE IF NOT EXISTS download_checkpoints (
    task_id VARCHAR(100) PRIMARY KEY,
    data_type VARCHAR(50) NOT NULL,           -- 数据类型：'daily', 'minute', 'tick'
    symbol VARCHAR(10),                        -- 股票代码（批量下载时为NULL）
    symbols TEXT,                              -- 股票代码列表（JSON格式）
    start_date DATE NOT NULL,                  -- 开始日期
    end_date DATE NOT NULL,                    -- 结束日期
    last_completed_date DATE,                  -- 最后完成的日期
    completed_symbols TEXT,                    -- 已完成的股票代码列表（JSON格式）
    progress_percent FLOAT DEFAULT 0.0,        -- 进度百分比
    total_items INTEGER DEFAULT 0,             -- 总项目数
    completed_items INTEGER DEFAULT 0,         -- 已完成项目数
    status VARCHAR(20) DEFAULT 'running',      -- 状态：'running', 'paused', 'completed', 'failed'
    error_message TEXT,                        -- 错误信息
    retry_count INTEGER DEFAULT 0,             -- 重试次数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_download_checkpoints_status ON download_checkpoints(status);
CREATE INDEX IF NOT EXISTS idx_download_checkpoints_data_type ON download_checkpoints(data_type);
CREATE INDEX IF NOT EXISTS idx_download_checkpoints_symbol ON download_checkpoints(symbol);
CREATE INDEX IF NOT EXISTS idx_download_checkpoints_updated_at ON download_checkpoints(updated_at);

-- 触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_download_checkpoints_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_download_checkpoints_updated_at
BEFORE UPDATE ON download_checkpoints
FOR EACH ROW
EXECUTE FUNCTION update_download_checkpoints_updated_at();

-- ============================================================
-- 下载任务日志表
-- ============================================================
CREATE TABLE IF NOT EXISTS download_task_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    event_type VARCHAR(50) NOT NULL,          -- 事件类型：'started', 'progress', 'completed', 'failed', 'resumed'
    message TEXT,                              -- 日志消息
    details JSONB,                             -- 详细信息（JSON格式）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_download_task_logs_task_id ON download_task_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_download_task_logs_event_type ON download_task_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_download_task_logs_created_at ON download_task_logs(created_at);

-- ============================================================
-- 注释
-- ============================================================
COMMENT ON TABLE download_checkpoints IS '下载检查点表，用于断点续传';
COMMENT ON COLUMN download_checkpoints.task_id IS '任务唯一标识';
COMMENT ON COLUMN download_checkpoints.data_type IS '数据类型';
COMMENT ON COLUMN download_checkpoints.status IS '任务状态：running/paused/completed/failed';
COMMENT ON COLUMN download_checkpoints.progress_percent IS '任务进度百分比';

COMMENT ON TABLE download_task_logs IS '下载任务日志表';
COMMENT ON COLUMN download_task_logs.event_type IS '事件类型：started/progress/completed/failed/resumed';
