-- 添加涨跌停列表定时任务
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    points_consumption,
    cron_expression,
    enabled,
    description
) VALUES (
    'limit_list',
    'limit_list',
    '涨跌停列表',
    '打板专题',
    552,
    5000,
    '0 18 * * *',
    false,
    '同步每日涨跌停、炸板数据（包含行情数据、封板数据、连板统计等）（5000积分/次，单次最大2500行，数据从2020年开始）'
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;
