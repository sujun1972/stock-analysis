-- 新增财务审计意见定时任务
-- 对应 task_metadata.py 中已有的 tasks.sync_fina_audit

INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES (
    'tasks.sync_fina_audit',
    'tasks.sync_fina_audit',
    '财务审计意见',
    '同步上市公司定期财务审计意见数据（审计结果、审计费用、会计事务所等，500积分/次）',
    '财务数据',
    806,
    500,
    '0 3 * * 6',
    true,
    '{}'
)
ON CONFLICT DO NOTHING;
