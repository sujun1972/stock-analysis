-- 添加中央结算系统持股汇总定时任务
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
    'tasks.sync_ccass_hold',
    'ccass_hold',
    '中央结算系统持股汇总',
    '获取中央结算系统持股汇总数据，覆盖全部历史数据，根据交易所披露时间，当日数据在下一交易日早上9点前完成入库（120积分试用，5000积分正式，每分钟可请求300-500次，单次最大5000条）',
    '0 9 * * *',  -- 每天早上9点执行
    false,  -- 默认禁用
    '{"ts_code": null, "hk_code": null, "trade_date": null, "start_date": null, "end_date": null}'::jsonb,
    '特色数据',
    403,
    5000,
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

-- 添加注释
COMMENT ON COLUMN scheduled_tasks.task_name IS '任务名称（唯一标识）';
COMMENT ON COLUMN scheduled_tasks.category IS '任务分类（基础数据、扩展数据、特色数据、参考数据、打板专题、财务数据等）';
