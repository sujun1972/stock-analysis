-- 添加港股通每日成交统计定时任务
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
    'tasks.sync_ggt_daily',
    'ggt_daily',
    '港股通每日成交统计',
    '获取港股通每日成交信息，数据从2014年开始（Tushare ggt_daily接口，2000积分/次）',
    '0 19 * * 1-5',
    false,
    '{}',
    '行情数据',
    210,
    2000
) ON CONFLICT (task_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption;
