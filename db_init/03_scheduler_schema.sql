-- ================================================
-- Scheduler Schema
-- A股AI交易系统 - 定时任务调度引擎
-- ================================================

-- 1. 定时任务配置表
-- 存储各类数据同步的定时任务配置
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id SERIAL PRIMARY KEY,
    task_name VARCHAR(100) UNIQUE NOT NULL,         -- 任务名称 (唯一标识)
    module VARCHAR(50) NOT NULL,                    -- 模块名称: stock_list, new_stocks, delisted_stocks, daily, minute, realtime
    description TEXT,                                -- 任务描述
    cron_expression VARCHAR(100),                    -- Cron表达式 (例: "0 9 * * 1-5" 表示工作日9点)
    enabled BOOLEAN DEFAULT false,                   -- 是否启用
    params JSONB,                                    -- 任务参数 (JSON格式, 如 {"days": 30})
    last_run_at TIMESTAMP,                          -- 上次运行时间
    next_run_at TIMESTAMP,                          -- 下次运行时间
    last_status VARCHAR(20),                        -- 上次运行状态: success, failed
    last_error TEXT,                                -- 上次错误信息
    run_count INTEGER DEFAULT 0,                    -- 运行次数
    created_by VARCHAR(50) DEFAULT 'system',        -- 创建者
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_module ON scheduled_tasks(module);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_enabled ON scheduled_tasks(enabled);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run ON scheduled_tasks(next_run_at);

-- 2. 任务执行历史表
-- 记录每次定时任务的执行情况
CREATE TABLE IF NOT EXISTS task_execution_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
    task_name VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,                    -- 状态: running, success, failed
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    result_summary JSONB,                           -- 执行结果摘要 (JSON格式)
    error_message TEXT,                             -- 错误信息
    sync_log_id INTEGER                             -- 关联的sync_log记录ID
);

CREATE INDEX IF NOT EXISTS idx_execution_history_task_id ON task_execution_history(task_id);
CREATE INDEX IF NOT EXISTS idx_execution_history_status ON task_execution_history(status);
CREATE INDEX IF NOT EXISTS idx_execution_history_started ON task_execution_history(started_at DESC);

-- 3. 插入默认定时任务配置
INSERT INTO scheduled_tasks (task_name, module, description, cron_expression, enabled, params)
VALUES
    ('daily_stock_list_sync', 'stock_list', '每日股票列表同步', '0 1 * * *', false, '{}'),
    ('daily_new_stocks_sync', 'new_stocks', '每日新股列表同步', '0 2 * * *', false, '{"days": 30}'),
    ('weekly_delisted_stocks_sync', 'delisted_stocks', '每周退市列表同步', '0 3 * * 0', false, '{}'),
    ('daily_data_sync', 'daily', '每日日线数据同步', '0 18 * * 1-5', false, '{"max_stocks": 100}')
ON CONFLICT (task_name) DO NOTHING;

-- 4. 触发器：自动更新 updated_at
DROP TRIGGER IF EXISTS update_scheduled_tasks_updated_at ON scheduled_tasks;
CREATE TRIGGER update_scheduled_tasks_updated_at BEFORE UPDATE ON scheduled_tasks
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 5. 视图：活跃的定时任务
CREATE OR REPLACE VIEW v_active_scheduled_tasks AS
SELECT
    id,
    task_name,
    module,
    description,
    cron_expression,
    params,
    last_run_at,
    next_run_at,
    last_status,
    run_count,
    enabled
FROM scheduled_tasks
WHERE enabled = true
ORDER BY next_run_at ASC;

-- 6. 视图：最近任务执行历史
CREATE OR REPLACE VIEW v_recent_task_executions AS
SELECT
    h.id,
    h.task_name,
    h.module,
    h.status,
    h.started_at,
    h.completed_at,
    h.duration_seconds,
    h.result_summary,
    h.error_message,
    t.cron_expression
FROM task_execution_history h
LEFT JOIN scheduled_tasks t ON h.task_id = t.id
ORDER BY h.started_at DESC
LIMIT 50;

-- 完成
COMMENT ON TABLE scheduled_tasks IS '定时任务配置表';
COMMENT ON TABLE task_execution_history IS '任务执行历史表';
