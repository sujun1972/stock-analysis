-- 添加股票回购数据同步任务到定时任务表
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    points_consumption,
    cron_expression,
    enabled,
    description,
    created_at,
    updated_at
) VALUES (
    'tasks.sync_repurchase',
    'reference_data',
    '股票回购',
    '参考数据',
    454,
    600,
    '0 0 0 * * *',  -- 每天0点执行（默认禁用，需手动启用）
    false,
    '获取上市公司回购股票数据，包括回购公告日期、回购进度、回购数量、回购金额、回购价格区间等（600积分/次）',
    NOW(),
    NOW()
)
ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description,
    updated_at = NOW();
