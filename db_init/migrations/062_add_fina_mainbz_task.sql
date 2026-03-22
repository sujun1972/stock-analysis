-- 添加主营业务构成同步任务到定时任务表
INSERT INTO scheduled_tasks (
    task_name,
    module,
    display_name,
    category,
    display_order,
    points_consumption,
    enabled,
    cron_expression,
    description
) VALUES (
    'tasks.sync_fina_mainbz',
    'tasks.sync_fina_mainbz',
    '主营业务构成',
    '财务数据',
    807,
    2000,
    false,
    '0 3 * * 0',
    '同步上市公司主营业务构成数据（按产品/地区/行业分类，2000积分/次）'
)
ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description,
    updated_at = NOW();
