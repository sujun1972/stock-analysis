-- ============================================================
-- V012: 添加 Celery 异步任务支持
-- ============================================================
-- 为 strategy_executions 表添加 task_id 字段以支持异步任务跟踪
-- 创建日期: 2026-03-03
-- 作者: Backend Team
-- ============================================================

-- 1. 添加 task_id 字段用于跟踪 Celery 任务
ALTER TABLE strategy_executions
ADD COLUMN task_id VARCHAR(255) UNIQUE;

-- 2. 为 task_id 创建索引以加速查询
CREATE INDEX idx_exec_task_id ON strategy_executions(task_id) WHERE task_id IS NOT NULL;

-- 3. 添加注释说明字段用途
COMMENT ON COLUMN strategy_executions.task_id IS 'Celery异步任务ID，用于追踪长时间运行的回测任务';
COMMENT ON COLUMN strategy_executions.error_message IS '执行失败时的详细错误信息（已存在字段，此处仅添加注释）';
