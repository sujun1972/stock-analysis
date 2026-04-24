-- 价值度量定时任务：flush 每 5 分钟捞 dirty set；all 每日 16:30 兜底全市场重算
BEGIN;

INSERT INTO scheduled_tasks
    (task_name, module, description, cron_expression, enabled, params,
     display_name, category, display_order, points_consumption)
VALUES
    ('tasks.recompute_value_metrics_flush',
     'tasks.recompute_value_metrics_flush',
     '从 Redis value_metrics:dirty 集合捞出脏股票批量重算 ROC / EY / 内在价值。',
     '*/5 * * * *',
     TRUE,
     '{}'::jsonb,
     '价值度量（脏队列 flush）',
     '财务数据',
     1010,
     0),
    ('tasks.recompute_value_metrics_all',
     'tasks.recompute_value_metrics_all',
     '全市场重算 ROC / EY / 内在价值，日终收盘后兜底（16:30，交易日）。',
     '30 16 * * 1-5',
     TRUE,
     '{"source":"beat_daily"}'::jsonb,
     '价值度量（全市场重算）',
     '财务数据',
     1011,
     0)
ON CONFLICT (task_name) DO UPDATE
    SET cron_expression = EXCLUDED.cron_expression,
        description     = EXCLUDED.description,
        display_name    = EXCLUDED.display_name,
        category        = EXCLUDED.category,
        display_order   = EXCLUDED.display_order,
        params          = EXCLUDED.params,
        enabled         = EXCLUDED.enabled,
        updated_at      = CURRENT_TIMESTAMP;

COMMIT;
