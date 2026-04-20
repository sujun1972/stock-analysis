-- 注册公司公告增量同步到 scheduled_tasks（可在调度管理页面启用 / 配置 cron）
-- 数据源：AkShare 东方财富聚合（免费，不消耗 Tushare 积分）

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
    'tasks.sync_stock_anns',
    'tasks.sync_stock_anns',
    '公司公告（增量）',
    '同步 A 股公司公告（来源：AkShare 东方财富聚合，免费替代 Tushare anns_d）。逐交易日拉全市场公告并入库，默认回看 7 天；单日接口耗时 60~120s。',
    '新闻公告',
    600,
    '30 18 * * 1-5',  -- 每个工作日 18:30（盘后 30 分钟，给东方财富更新留窗口）
    FALSE,            -- 默认禁用，由管理员按需启用
    '{}',
    0
) ON CONFLICT (task_name) DO UPDATE SET
    module             = EXCLUDED.module,
    display_name       = EXCLUDED.display_name,
    description        = EXCLUDED.description,
    category           = EXCLUDED.category,
    display_order      = EXCLUDED.display_order,
    points_consumption = EXCLUDED.points_consumption,
    updated_at         = NOW();
