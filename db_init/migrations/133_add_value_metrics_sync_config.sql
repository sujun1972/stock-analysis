-- sync_configs 登记：价值度量全市场重算入口（供同步配置页手动触发）
-- 只有全量入口；增量走 dirty set 自动触发，不需人工触发
BEGIN;

INSERT INTO sync_configs
    (table_key, display_name, category, display_order,
     incremental_task_name, full_sync_task_name, full_sync_strategy,
     full_sync_concurrency, description, data_source, api_limit)
VALUES
    ('stock_value_metrics',
     '价值度量（ROC/EY/内在价值）',
     '财务数据',
     1010,
     NULL,
     'tasks.recompute_value_metrics_all',
     'snapshot',
     1,
     '魔法公式 ROC / EY（《股市稳赚》）+ 格雷厄姆内在价值（《聪明的投资者》）。'
     || E'数据来自 income / balancesheet / daily_basic / report_rc 的最新快照现场计算；'
     || E'5 源同步完成后自动塞 Redis dirty set，Celery Beat 每 5 分钟 flush 合批重算。'
     || E'手动全量按钮仅用于修 bug 或首次初始化。',
     'internal',
     0)
ON CONFLICT (table_key) DO UPDATE
    SET display_name        = EXCLUDED.display_name,
        category            = EXCLUDED.category,
        display_order       = EXCLUDED.display_order,
        full_sync_task_name = EXCLUDED.full_sync_task_name,
        full_sync_strategy  = EXCLUDED.full_sync_strategy,
        description         = EXCLUDED.description,
        updated_at          = CURRENT_TIMESTAMP;

COMMIT;
