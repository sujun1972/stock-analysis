-- 宏观经济指标 scheduled_tasks + sync_configs 注册（Phase 3 of news_anns roadmap）
-- 数据源：AkShare 免费宏观接口（无参数，每次返回完整历史序列）

-- ------------------------------------------------------------------
-- scheduled_tasks（增量）
-- ------------------------------------------------------------------
INSERT INTO scheduled_tasks (
    task_name, module, display_name, description, category,
    display_order, cron_expression, enabled, params, points_consumption
) VALUES (
    'tasks.sync_macro_indicators',
    'tasks.sync_macro_indicators',
    '宏观经济指标（增量）',
    '同步中国宏观经济指标（AkShare 免费接口，替代 Tushare eco_cal）：CPI/PPI/PMI/M2/新增社融/GDP/Shibor。各指标接口无日期参数，每次拉取完整历史并 UPSERT；每日一次覆盖足够。',
    '新闻公告',
    630,
    '15 19 * * *',  -- 每日 19:15（月度指标通常在月中 9-15 号前后公布，日级 Shibor 每日更新）
    FALSE,          -- 默认禁用，由管理员按需启用
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


INSERT INTO scheduled_tasks (
    task_name, module, display_name, description, category,
    display_order, cron_expression, enabled, params, points_consumption
) VALUES (
    'tasks.sync_macro_indicators_full_history',
    'tasks.sync_macro_indicators_full_history',
    '宏观经济指标（全量历史）',
    'AkShare 宏观接口不支持日期参数，全量等价于一次增量（把全部历史 UPSERT 一遍）；按钮仅为同步配置页面兼容。',
    '新闻公告',
    631,
    '0 3 1 * *',    -- 每月 1 日 03:00（低频兜底，避免与增量撞车）
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
    'macro_indicators', '宏观经济指标', '新闻公告', 630,
    'tasks.sync_macro_indicators', 0,  -- 占位（接口无日期参数，回看天数无效）
    'tasks.sync_macro_indicators_full_history', 'snapshot', 1,
    FALSE, NULL,
    '/news-anns/macro-indicators', '/macro-indicators', 0,
    'AkShare 宏观接口（CPI/PPI/PMI/M2/新增社融/GDP/Shibor），免费数据源。接口无日期参数，每次返回完整历史序列并 UPSERT；单次总耗时 ~2-3 分钟。',
    10000
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
