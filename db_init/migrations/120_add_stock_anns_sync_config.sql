-- 注册公司公告到 sync_configs（驱动同步配置页面展示 + 同步按钮）
-- 数据源：AkShare 东方财富聚合（免费），类别独立："新闻公告"
-- 策略：
--   - 增量：by_date（逐交易日）
--   - 全量：by_date + Redis Set 续继
--   - 被动：允许（用户打开个股 AI 分析时静默触发 tasks.sync_stock_anns_single）

INSERT INTO sync_configs (
    table_key, display_name, category, display_order,
    incremental_task_name, incremental_default_days,
    full_sync_task_name, full_sync_strategy, full_sync_concurrency,
    passive_sync_enabled, passive_sync_task_name,
    page_url, api_prefix, points_consumption, notes,
    api_limit
) VALUES
(
    'stock_anns',        '公司公告',           '新闻公告', 600,
    'tasks.sync_stock_anns', 7,
    'tasks.sync_stock_anns_full_history', 'by_date', 5,
    TRUE, 'tasks.sync_stock_anns_single',
    '/news-anns', '/stock-anns', 0,
    'AkShare 东方财富聚合，免费数据源。全市场接口单日 60~120s，全量覆盖可在此把起始日期改短以控制耗时。',
    5000
)
ON CONFLICT (table_key) DO UPDATE SET
    display_name             = EXCLUDED.display_name,
    category                 = EXCLUDED.category,
    display_order            = EXCLUDED.display_order,
    incremental_task_name    = EXCLUDED.incremental_task_name,
    incremental_default_days = EXCLUDED.incremental_default_days,
    full_sync_task_name      = EXCLUDED.full_sync_task_name,
    full_sync_strategy       = EXCLUDED.full_sync_strategy,
    full_sync_concurrency    = EXCLUDED.full_sync_concurrency,
    passive_sync_enabled     = EXCLUDED.passive_sync_enabled,
    passive_sync_task_name   = EXCLUDED.passive_sync_task_name,
    page_url                 = EXCLUDED.page_url,
    api_prefix               = EXCLUDED.api_prefix,
    points_consumption       = EXCLUDED.points_consumption,
    notes                    = EXCLUDED.notes,
    api_limit                = EXCLUDED.api_limit,
    updated_at               = NOW();
