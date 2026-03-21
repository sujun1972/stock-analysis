-- 添加股权质押统计定时任务配置

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
    points_consumption,
    created_at,
    updated_at
) VALUES (
    'tasks.sync_pledge_stat',
    'pledge_stat',
    '股权质押统计',
    '获取股票质押统计数据，包括质押次数、无限售/限售股质押数量、总股本、质押比例等（500积分/次，单次最大1000行）',
    '0 10 * * *',  -- 每天10:00执行
    FALSE,  -- 默认禁用，需要手动启用
    '{}',
    '参考数据',
    453,
    500,
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
