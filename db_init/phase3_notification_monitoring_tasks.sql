-- ========================================
-- Phase 3: 通知系统监控定时任务配置
-- ========================================
-- 描述: 添加通知系统健康检查和清理任务到定时任务表
-- 创建时间: 2026-03-15
-- ========================================

-- 1. 通知系统健康检查任务（每小时执行）
INSERT INTO scheduler_tasks (
    name,
    task_name,
    schedule_type,
    cron_expression,
    is_enabled,
    description,
    priority,
    timeout,
    max_retry,
    created_at,
    updated_at
) VALUES (
    'notification_health_check',
    'app.tasks.notification_tasks.notification_health_check_task',
    'cron',
    '0 * * * *',  -- 每小时整点执行
    true,
    '【通知系统】健康检查任务 - 每小时检查发送成功率、失败率、积压情况，发现异常自动告警管理员',
    8,  -- 中等优先级
    600,  -- 超时时间 10 分钟
    2,  -- 最多重试 2 次
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (name) DO UPDATE SET
    task_name = EXCLUDED.task_name,
    cron_expression = EXCLUDED.cron_expression,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;


-- 2. 清理过期站内消息任务（每天凌晨 2 点执行）
INSERT INTO scheduler_tasks (
    name,
    task_name,
    schedule_type,
    cron_expression,
    is_enabled,
    description,
    priority,
    timeout,
    max_retry,
    created_at,
    updated_at
) VALUES (
    'cleanup_expired_notifications',
    'app.tasks.notification_tasks.cleanup_expired_notifications_task',
    'cron',
    '0 2 * * *',  -- 每天凌晨 2:00 执行
    true,
    '【通知系统】清理过期站内消息 - 删除 3 个月前的已读消息，释放存储空间',
    5,  -- 较低优先级
    1800,  -- 超时时间 30 分钟
    1,  -- 最多重试 1 次
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (name) DO UPDATE SET
    task_name = EXCLUDED.task_name,
    cron_expression = EXCLUDED.cron_expression,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;


-- 3. 重置每日频率限制计数器（每天凌晨 0 点执行）
INSERT INTO scheduler_tasks (
    name,
    task_name,
    schedule_type,
    cron_expression,
    is_enabled,
    description,
    priority,
    timeout,
    max_retry,
    created_at,
    updated_at
) VALUES (
    'reset_daily_rate_limits',
    'app.tasks.notification_tasks.reset_daily_rate_limits_task',
    'cron',
    '0 0 * * *',  -- 每天凌晨 0:00 执行
    true,
    '【通知系统】重置每日频率限制 - 重置所有用户的每日通知计数，防止误限流',
    10,  -- 高优先级
    300,  -- 超时时间 5 分钟
    2,  -- 最多重试 2 次
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (name) DO UPDATE SET
    task_name = EXCLUDED.task_name,
    cron_expression = EXCLUDED.cron_expression,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;


-- ========================================
-- 查询验证
-- ========================================
-- 查看新添加的通知系统定时任务
SELECT
    name,
    task_name,
    cron_expression,
    is_enabled,
    description,
    priority
FROM scheduler_tasks
WHERE name IN (
    'notification_health_check',
    'cleanup_expired_notifications',
    'reset_daily_rate_limits'
)
ORDER BY priority DESC;
