-- 添加股东增减持定时任务
INSERT INTO scheduled_tasks (
    task_name,
    module,
    cron_expression,
    enabled,
    params,
    description,
    display_name,
    category,
    display_order,
    points_consumption
) VALUES (
    'tasks.sync_stk_holdertrade',
    'tasks.sync_stk_holdertrade',
    '0 18 * * *',
    false,
    '{"ts_code": null, "ann_date": null, "start_date": null, "end_date": null, "trade_type": null, "holder_type": null}',
    '获取上市公司股东增减持数据，了解重要股东近期及历史上的股份增减变化（2000积分/次，单次最大3000行）',
    '股东增减持',
    '参考数据',
    457,
    2000
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = CURRENT_TIMESTAMP;
