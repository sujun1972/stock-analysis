-- 添加龙虎榜机构明细定时任务配置
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
    points_consumption
) VALUES (
    'top_inst',
    'top_inst',
    '龙虎榜机构明细',
    '同步龙虎榜机构成交明细数据（营业部名称、买卖类型、买入额、卖出额、净成交额等）（5000积分/次，单次最大10000行）',
    '打板专题',
    551,
    '0 18 * * 1-5',  -- 每个工作日 18:00 执行
    false,  -- 默认禁用
    '{}',
    5000
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    category = EXCLUDED.category,
    display_order = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at = NOW();
