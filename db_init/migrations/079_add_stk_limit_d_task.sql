-- 添加每日涨跌停价格定时任务

INSERT INTO scheduled_tasks (
    task_name,
    display_name,
    module,
    cron_expression,
    enabled,
    description,
    category,
    display_order,
    points_consumption
)
VALUES (
    'tasks.sync_stk_limit_d',
    '每日涨跌停价格',
    'stk_limit_d_tasks',
    '0 9 * * *',  -- 每天早上9点执行
    false,  -- 默认禁用，用户可手动启用
    '获取全市场每日涨跌停价格，包括涨停价格、跌停价格等（每交易日8:40更新，2000积分/次，单次最大5800条）',
    '行情数据',
    220,
    2000
)
ON CONFLICT (task_name) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    module = EXCLUDED.module,
    cron_expression = EXCLUDED.cron_expression,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = NOW();
