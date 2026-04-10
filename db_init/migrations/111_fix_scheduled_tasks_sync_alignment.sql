-- 修复 scheduled_tasks.module 与 sync_configs.incremental_task_name 不一致问题
-- 目标：所有数据同步类定时任务，点击"执行"时调用的 Celery 任务与同步配置页"增量"按钮一致
--
-- 问题根因：以下4条记录的 module 字段指向旧的 extended.* 任务或无效值，
--           导致定时任务"执行"走 ExtendedDataSyncService，而同步配置页"增量"走新的独立 Service
--
-- 修复映射：
--   id=8  sync_daily_basic:  extended.sync_daily_basic  → tasks.sync_daily_basic
--   id=13 sync_adj_factor:   extended.sync_adj_factor   → tasks.sync_adj_factor
--   id=14 sync_block_trade:  extended.sync_block_trade  → tasks.sync_block_trade
--   id=27 sync_margin_secs:  sync_margin_secs(无效)     → extended.sync_margin_secs
--
-- 验证方式：确认与 sync_configs.incremental_task_name 完全一致
--   SELECT sc.table_key, sc.incremental_task_name, st.module
--   FROM sync_configs sc
--   JOIN scheduled_tasks st ON st.task_name IN ('sync_daily_basic','sync_adj_factor','tasks.sync_block_trade','sync_margin_secs')
--   WHERE sc.table_key IN ('daily_basic','adj_factor','block_trade','margin_secs');

UPDATE scheduled_tasks SET module = 'tasks.sync_daily_basic',    updated_at = NOW() WHERE id = 8;
UPDATE scheduled_tasks SET module = 'tasks.sync_adj_factor',     updated_at = NOW() WHERE id = 13;
UPDATE scheduled_tasks SET module = 'tasks.sync_block_trade',    updated_at = NOW() WHERE id = 14;
UPDATE scheduled_tasks SET module = 'extended.sync_margin_secs', updated_at = NOW() WHERE id = 27;
