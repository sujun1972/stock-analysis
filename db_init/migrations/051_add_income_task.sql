-- 添加利润表同步任务到定时任务表
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    points_consumption,
    enabled,
    cron_expression,
    description
) VALUES (
    'tasks.sync_income',
    'tasks.income_tasks',
    '利润表数据',
    '财务数据',
    800,
    2000,
    false,
    '0 1 * * *',
    '同步上市公司利润表数据（营业收入、净利润、每股收益等）'
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description;
