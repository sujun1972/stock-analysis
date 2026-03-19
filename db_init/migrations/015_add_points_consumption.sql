-- 为 scheduled_tasks 表添加积分消耗字段
-- 用于记录每个任务的Tushare积分消耗情况

ALTER TABLE scheduled_tasks
  ADD COLUMN IF NOT EXISTS points_consumption INTEGER;

-- 添加字段注释
COMMENT ON COLUMN scheduled_tasks.points_consumption IS 'Tushare积分消耗（每次执行消耗的积分数，NULL表示不消耗或未知）';

-- 初始化已知任务的积分消耗值
UPDATE scheduled_tasks SET points_consumption = 120 WHERE task_name = 'sync_daily_basic';
UPDATE scheduled_tasks SET points_consumption = 2000 WHERE task_name = 'sync_moneyflow';
UPDATE scheduled_tasks SET points_consumption = 2000 WHERE task_name = 'sync_moneyflow_hsgt';
UPDATE scheduled_tasks SET points_consumption = 120 WHERE task_name = 'sync_moneyflow_mkt_dc';
UPDATE scheduled_tasks SET points_consumption = 6000 WHERE task_name = 'sync_moneyflow_ind_dc';
UPDATE scheduled_tasks SET points_consumption = 5000 WHERE task_name = 'sync_moneyflow_stock_dc';
UPDATE scheduled_tasks SET points_consumption = 300 WHERE task_name = 'sync_margin';
UPDATE scheduled_tasks SET points_consumption = 120 WHERE task_name = 'sync_stk_limit';
UPDATE scheduled_tasks SET points_consumption = 300 WHERE task_name = 'sync_block_trade';
UPDATE scheduled_tasks SET points_consumption = 120 WHERE task_name = 'sync_adj_factor';
UPDATE scheduled_tasks SET points_consumption = 120 WHERE task_name = 'sync_suspend';

-- 验证更新结果
SELECT task_name, display_name, points_consumption
FROM scheduled_tasks
WHERE points_consumption IS NOT NULL
ORDER BY points_consumption DESC;
