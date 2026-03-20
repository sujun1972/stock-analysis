-- 添加融资融券标的（盘前更新）定时任务

INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    category,
    display_order,
    cron_expression,
    enabled,
    params,
    points_consumption,
    created_at,
    updated_at
) VALUES (
    'sync_margin_secs',
    'extended',
    '融资融券标的（盘前更新）',
    '同步沪深京三大交易所融资融券标的（包括ETF），每天盘前更新',
    '两融及转融通',
    520,  -- 显示顺序：在两融数据分类中排第3位（融资融券汇总500、明细510、标的520）
    '0 8 * * *',  -- 每日8:00（盘前更新）
    false,  -- 默认禁用（高积分消耗）
    '{}',
    2000,  -- 积分消耗：2000
    NOW(),
    NOW()
)
ON CONFLICT (task_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = NOW();
