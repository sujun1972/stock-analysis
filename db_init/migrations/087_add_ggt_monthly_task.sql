-- 添加港股通每月成交统计定时任务
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    cron_expression,
    enabled,
    params,
    category,
    display_order,
    points_consumption
) VALUES (
    'tasks.sync_ggt_monthly',
    'ggt_monthly',
    '港股通每月成交统计',
    '获取港股通每月成交信息，数据从2014年开始，单次最大1000条（Tushare ggt_monthly接口，5000积分/次）',
    '0 20 1 * *',
    false,
    '{}',
    '行情数据',
    271,
    5000
) ON CONFLICT (task_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption;
