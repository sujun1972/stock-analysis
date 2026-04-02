-- 新增港股通每月成交统计定时任务
-- 对应 task_metadata.py 中已有的 tasks.sync_ggt_monthly

INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES (
    'tasks.sync_ggt_monthly',
    'tasks.sync_ggt_monthly',
    '港股通每月成交统计',
    '获取港股通每月成交信息，数据从2014年开始，单次最大1000条（Tushare ggt_monthly接口，5000积分/次）',
    '行情数据',
    271,
    5000,
    '0 4 2 * *',
    true,
    '{}'
)
ON CONFLICT DO NOTHING;
