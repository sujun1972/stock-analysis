-- 添加业绩快报同步任务到 scheduled_tasks 表

INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    description,
    enabled,
    cron_expression,
    category,
    display_order,
    points_consumption,
    created_at,
    updated_at
) VALUES (
    'tasks.sync_express',
    'express',
    '业绩快报',
    '获取上市公司业绩快报，包括营业收入、利润、资产、每股收益、净资产收益率、同比增长率等（2000积分/次）',
    false,
    '0 8 * * *',
    '财务数据',
    479,
    2000,
    NOW(),
    NOW()
) ON CONFLICT (task_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = NOW();

COMMENT ON COLUMN scheduled_tasks.task_name IS '任务名称（Celery任务名）';
COMMENT ON COLUMN scheduled_tasks.display_name IS '任务显示名称';
COMMENT ON COLUMN scheduled_tasks.description IS '任务描述';
COMMENT ON COLUMN scheduled_tasks.category IS '任务分类';
COMMENT ON COLUMN scheduled_tasks.display_order IS '显示排序号';
COMMENT ON COLUMN scheduled_tasks.points_consumption IS 'Tushare积分消耗';
