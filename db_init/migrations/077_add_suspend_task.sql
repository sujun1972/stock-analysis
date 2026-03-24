-- 添加每日停复牌信息同步任务到定时任务表

INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    category,
    display_order,
    cron_expression,
    enabled,
    created_at,
    updated_at
) VALUES (
    'tasks.sync_suspend',
    'tasks',
    '每日停复牌信息',
    '按日期方式获取股票每日停复牌信息，包括停牌时间段、停复牌类型等（不定期更新）',
    '行情数据',
    210,
    '0 16 * * 1-5',  -- 每个工作日下午4点执行
    false,  -- 默认禁用，用户可手动启用
    NOW(),
    NOW()
) ON CONFLICT (task_name) DO NOTHING;
