-- 添加神奇九转指标定时任务
-- 由于涉及分钟数据,每天21点更新

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
    'tasks.sync_stk_nineturn',
    'stk_nineturn',
    '神奇九转指标',
    '特色数据',
    408,
    6000,
    '0 21 * * 1-5',  -- 每个交易日21:00执行(周一到周五)
    false,  -- 默认禁用,需要用户手动开启
    '神奇九转(又称"九转序列")是一种基于技术分析的股票趋势反转指标,通过识别连续9天的特定走势来判断潜在反转点。数据从2023年开始,每天21点更新,涉及分钟数据(6000积分/次,单次最大10000行)',
    NOW(),
    NOW()
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    description = EXCLUDED.description,
    updated_at = NOW();

-- 添加注释
COMMENT ON COLUMN scheduled_tasks.cron_expression IS 'Cron表达式 (格式: 分 时 日 月 周)';

-- 查询确认
SELECT id, task_name, display_name, cron_expression, enabled, description
FROM scheduled_tasks
WHERE task_name = 'tasks.sync_stk_nineturn';
