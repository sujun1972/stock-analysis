-- 新闻联播（cctv_news）scheduled_tasks + sync_configs 注册（Phase 2 of news_anns roadmap）
-- 数据源：AkShare news_cctv（按自然日，支持 2016-02 起）

-- ------------------------------------------------------------------
-- scheduled_tasks（增量：每晚 19:45 拉当日联播，新闻联播 19:00 播出留 45 分钟缓冲）
-- ------------------------------------------------------------------
INSERT INTO scheduled_tasks (
    task_name, module, display_name, description, category,
    display_order, cron_expression, enabled, params, points_consumption
) VALUES (
    'tasks.sync_cctv_news',
    'tasks.sync_cctv_news',
    '新闻联播（增量）',
    '同步新闻联播文字稿（来源：AkShare news_cctv，免费，替代 Tushare cctv_news）。按自然日逐日抓取，默认回看 3 天以容错。单日接口耗时 3-8s。',
    '新闻公告',
    620,
    '45 19 * * *',  -- 每晚 19:45（联播 19:00 播出后）
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
-- sync_configs
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
    'cctv_news', '新闻联播', '新闻公告', 620,
    'tasks.sync_cctv_news', 3,  -- 默认回看 3 天（涵盖周末/假期后补抓）
    'tasks.sync_cctv_news_full_history', 'by_date', 1,
    FALSE, NULL,  -- 联播是全市场的，不需要被动单股同步
    '/news-anns/cctv-news', '/cctv-news', 0,
    'AkShare news_cctv，免费数据源，按自然日抓取（放假日返回空）。接口单日 3-8s，全量覆盖近 5 年约 1500 日、3-4 小时。',
    200
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
