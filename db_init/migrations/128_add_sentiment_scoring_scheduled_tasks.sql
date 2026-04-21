-- 舆情情绪打分任务注册（scheduled_tasks；不写入 sync_configs）。
-- 这两个任务是对已同步数据的二次加工；同步完成后 Service 会主动派发（见
-- news_flash_sync_service / stock_anns_sync_service 的 _trigger_sentiment_scoring）。
-- 定时任务作为"扫尾"兜底：每 30 分钟扫一次，把漏打分的补上。

INSERT INTO scheduled_tasks (
    task_name, module, display_name, description, category,
    display_order, cron_expression, enabled, params, points_consumption
) VALUES
(
    'tasks.score_stock_anns_sentiment',
    'tasks.score_stock_anns_sentiment',
    '公告舆情打分（批量）',
    '批量给未打分公告打事件标签 + 情绪分（单次 30 条，Prompt 模板 anns_sentiment_v1）。同步完成后自动触发，定时任务作为扫尾兜底。',
    '新闻公告',
    640,
    '*/30 * * * *',
    FALSE,
    '{"limit": 30, "provider": null}',
    0
),
(
    'tasks.score_news_flash_sentiment',
    'tasks.score_news_flash_sentiment',
    '快讯舆情打分（批量）',
    '批量给 related_ts_codes 非空的未打分快讯打情绪分 + 主题标签（单次 30 条，Prompt 模板 news_flash_sentiment_v1）。',
    '新闻公告',
    641,
    '*/30 * * * *',
    FALSE,
    '{"limit": 30, "provider": null}',
    0
)
ON CONFLICT (task_name) DO UPDATE SET
    module             = EXCLUDED.module,
    display_name       = EXCLUDED.display_name,
    description        = EXCLUDED.description,
    category           = EXCLUDED.category,
    display_order      = EXCLUDED.display_order,
    params             = EXCLUDED.params,
    points_consumption = EXCLUDED.points_consumption,
    updated_at         = NOW();
