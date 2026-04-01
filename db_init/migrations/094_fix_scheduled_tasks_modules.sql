-- 修复 scheduled_tasks 表中 module 字段与 task_metadata.py key 不一致的问题
-- 以及将旧的 daily_data_sync (sync.daily_batch) 迁移到新的 tasks.sync_daily_single

-- 1. 旧的每日行情同步任务 (sync.daily_batch) → 新的全市场日线同步 (sync.daily_single)
UPDATE scheduled_tasks
SET
    task_name    = 'tasks.sync_daily_single',
    module       = 'tasks.sync_daily_single',
    display_name = '股票日线数据同步（全市场）',
    params       = '{}'
WHERE id = 4;

-- 2. 修正中文 task_name
UPDATE scheduled_tasks SET task_name = 'tasks.sync_margin_detail' WHERE id = 26;

-- 3. 批量修正 module 字段，与 task_metadata.py 中的 key 对齐
UPDATE scheduled_tasks SET module = 'quality.daily_report'            WHERE id = 16;
UPDATE scheduled_tasks SET module = 'quality.weekly_report'           WHERE id = 17;
UPDATE scheduled_tasks SET module = 'sync_margin_secs'                WHERE id = 27;
UPDATE scheduled_tasks SET module = 'limit_cpt'                       WHERE id = 36;
UPDATE scheduled_tasks SET module = 'tasks.sync_report_rc'            WHERE id = 38;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_alert'            WHERE id = 42;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_high_shock'       WHERE id = 44;
UPDATE scheduled_tasks SET module = 'tasks.sync_pledge_stat'          WHERE id = 45;
UPDATE scheduled_tasks SET module = 'tasks.sync_repurchase'           WHERE id = 47;
UPDATE scheduled_tasks SET module = 'tasks.sync_share_float'          WHERE id = 48;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_holdernumber'     WHERE id = 49;
UPDATE scheduled_tasks SET module = 'tasks.sync_income'               WHERE id = 52;
UPDATE scheduled_tasks SET module = 'tasks.sync_balancesheet'         WHERE id = 53;
UPDATE scheduled_tasks SET module = 'tasks.sync_cashflow'             WHERE id = 55;
UPDATE scheduled_tasks SET module = 'tasks.sync_forecast'             WHERE id = 57;
UPDATE scheduled_tasks SET module = 'tasks.sync_express'              WHERE id = 58;
UPDATE scheduled_tasks SET module = 'tasks.sync_dividend'             WHERE id = 61;
UPDATE scheduled_tasks SET module = 'tasks.sync_fina_indicator'       WHERE id = 62;
UPDATE scheduled_tasks SET module = 'tasks.sync_disclosure_date'      WHERE id = 68;
UPDATE scheduled_tasks SET module = 'tasks.sync_ccass_hold'           WHERE id = 69;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_nineturn'         WHERE id = 71;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_ah_comparison'    WHERE id = 72;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_surv'             WHERE id = 73;
UPDATE scheduled_tasks SET module = 'tasks.sync_suspend'              WHERE id = 75;
UPDATE scheduled_tasks SET module = 'tasks.sync_stk_limit_d'          WHERE id = 77;
UPDATE scheduled_tasks SET module = 'tasks.sync_hsgt_top10'           WHERE id = 79;
UPDATE scheduled_tasks SET module = 'tasks.sync_ggt_top10'            WHERE id = 80;
UPDATE scheduled_tasks SET module = 'tasks.sync_ggt_daily'            WHERE id = 81;
