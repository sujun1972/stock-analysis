-- 添加沪深股通十大成交股同步任务到定时任务表
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    cron_expression,
    enabled,
    description,
    created_at,
    updated_at
) VALUES (
    'tasks.sync_hsgt_top10',
    'hsgt_top10',
    '沪深股通十大成交股',
    '行情数据',
    250,
    '30 19 * * 1-5',
    false,
    '获取沪股通、深股通每日前十大成交详细数据，每天18~20点之间完成当日更新',
    NOW(),
    NOW()
)
ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    description = EXCLUDED.description,
    updated_at = NOW();
