-- 添加连板天梯同步任务到定时任务表

INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    points_consumption,
    enabled,
    cron_expression,
    description,
    params
) VALUES (
    'tasks.sync_limit_step',
    'limit_step',
    '连板天梯',
    '打板专题',
    610,
    8000,
    false,
    '0 17 * * 1-5',
    '获取每天连板个数晋级的股票，可以分析出每天连续涨停进阶个数，判断强势热度',
    '{}'
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description;
