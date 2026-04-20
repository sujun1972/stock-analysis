-- 财经快讯（news_flash）scheduled_tasks + sync_configs 注册（Phase 2 of news_anns roadmap）
-- 数据源：AkShare 财新要闻精选（无日期参数，每次返回最近 ~100 条）+ 东财个股新闻（按 ts_code）

-- ------------------------------------------------------------------
-- scheduled_tasks（增量）
-- ------------------------------------------------------------------
INSERT INTO scheduled_tasks (
    task_name, module, display_name, description, category,
    display_order, cron_expression, enabled, params, points_consumption
) VALUES (
    'tasks.sync_news_flash',
    'tasks.sync_news_flash',
    '财经快讯（增量）',
    '同步财新要闻精选（来源：AkShare stock_news_main_cx，免费，替代 Tushare news 接口）。接口无日期参数，每次拉最近 ~100 条；建议每 30 分钟执行一次以持续积累。',
    '新闻公告',
    610,
    '*/30 * * * *',  -- 每 30 分钟执行一次
    FALSE,
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


-- ------------------------------------------------------------------
-- sync_configs（同步配置页面驱动）
-- ------------------------------------------------------------------
INSERT INTO sync_configs (
    table_key, display_name, category, display_order,
    incremental_task_name, incremental_default_days,
    full_sync_task_name, full_sync_strategy, full_sync_concurrency,
    passive_sync_enabled, passive_sync_task_name,
    page_url, api_prefix, points_consumption, notes,
    api_limit
) VALUES
(
    'news_flash', '财经快讯', '新闻公告', 610,
    'tasks.sync_news_flash', 1,  -- 占位（接口无日期参数，回看天数无效）
    'tasks.sync_news_flash_full_history', 'snapshot', 1,
    TRUE, 'tasks.sync_news_flash_single',
    '/news-anns/news-flash', '/news-flash', 0,
    'AkShare 财新要闻精选（stock_news_main_cx）+ 东财个股新闻（stock_news_em），免费数据源。接口无日期回溯能力，靠日常增量积累历史。',
    100
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
