-- 补充两融及转融通分类下缺少的转融资交易汇总任务
-- 已有：融资融券交易汇总(510)、融资融券交易明细(515)、融资融券标的(520)
-- 新增：转融资交易汇总(525)

INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES (
    'tasks.sync_slb_len',
    'tasks.sync_slb_len',
    '转融资交易汇总',
    '同步转融通融资汇总数据（期初余额、竞价成交、再借成交、偿还、期末余额）（2000积分/次，单次最大5000行）',
    '两融及转融通',
    525,
    2000,
    '0 18 * * 1-5',
    true,
    '{}'
)
ON CONFLICT DO NOTHING;
