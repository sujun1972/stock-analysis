-- 修正打板专题分类任务排序，并补充缺少的3个任务
-- 菜单顺序：龙虎榜每日明细(1)、龙虎榜机构明细(2)、涨跌停列表(3)、连板天梯(4)、
--           最强板块统计(5)、东方财富板块数据(6)、东方财富板块成分(7)、东财概念板块行情(8)

-- 修正已有任务的排序（连板天梯 610→553，最强板块统计 554→554 不变）
UPDATE scheduled_tasks SET display_order = 553 WHERE module = 'limit_step';
UPDATE scheduled_tasks SET display_order = 554 WHERE module = 'limit_cpt';

-- 插入缺少的3个任务（东方财富板块数据、板块成分、概念板块行情）
INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES
    (
        'tasks.sync_dc_index',
        'tasks.sync_dc_index',
        '东方财富板块数据',
        '获取东方财富每个交易日的概念/行业/地域板块数据，支持按日期和板块类型查询（6000积分/次）',
        '打板专题',
        555,
        6000,
        '30 16 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_dc_member',
        'tasks.sync_dc_member',
        '东方财富板块成分',
        '获取东方财富板块每日成分数据，可根据概念板块代码和交易日期获取历史成分（6000积分/次）',
        '打板专题',
        556,
        6000,
        '0 17 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_dc_daily',
        'tasks.sync_dc_daily',
        '东财概念板块行情',
        '获取东方财富概念板块、行业指数板块、地域板块行情数据，历史数据从2020年开始（6000积分/次）',
        '打板专题',
        557,
        6000,
        '30 17 * * 1-5',
        true,
        '{}'
    )
ON CONFLICT DO NOTHING;
