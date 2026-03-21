-- 添加最强板块统计定时任务
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    category,
    display_order,
    points_consumption,
    cron_expression,
    enabled,
    created_at,
    updated_at
) VALUES (
    'limit_cpt',
    'tasks.sync_limit_cpt',
    '最强板块统计',
    '获取每天涨停股票最多最强的概念板块，可以分析强势板块的轮动，判断资金动向（8000积分以上每分钟500次，单次最大2000行）',
    '打板专题',
    554,
    8000,
    '0 18 * * *',  -- 每天18:00执行
    false,
    NOW(),
    NOW()
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = NOW();
