-- 为 celery_task_history 增加批量任务专用进度字段
-- 驱动批量 AI 分析任务（batch_ai_analysis）的前端进度展示
-- 已有 progress / metadata / params 对一次性任务够用，但批量任务需要成/败分桶计数
-- 新字段对所有任务类型通用，NULL 表示该任务不是分桶型批量任务

ALTER TABLE celery_task_history
    ADD COLUMN IF NOT EXISTS total_items INTEGER,
    ADD COLUMN IF NOT EXISTS completed_items INTEGER,
    ADD COLUMN IF NOT EXISTS success_items INTEGER,
    ADD COLUMN IF NOT EXISTS failed_items INTEGER;

COMMENT ON COLUMN celery_task_history.total_items IS '批量任务总条目数（股票数）';
COMMENT ON COLUMN celery_task_history.completed_items IS '已完成条目数（成功+失败）';
COMMENT ON COLUMN celery_task_history.success_items IS '成功条目数';
COMMENT ON COLUMN celery_task_history.failed_items IS '失败条目数';
