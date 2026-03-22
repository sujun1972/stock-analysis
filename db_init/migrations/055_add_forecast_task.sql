-- 添加业绩预告数据同步定时任务

INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    category,
    cron_expression,
    enabled,
    params,
    display_order,
    points_consumption
) VALUES (
    'tasks.sync_forecast',
    'forecast',
    '业绩预告',
    '获取业绩预告数据，包括公告日期、报告期、预告类型、净利润变动幅度、净利润预告值、业绩变动原因等（2000积分/次）',
    '财务数据',
    '0 9 * * *',  -- 每天9:00执行
    FALSE,  -- 默认不启用，需要手动启用
    '{}',
    478,
    2000
)
ON CONFLICT (task_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption;
