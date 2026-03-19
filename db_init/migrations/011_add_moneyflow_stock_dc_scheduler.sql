-- =====================================================
-- 添加个股资金流向（DC）定时任务
-- 创建时间：2026-03-19
-- 说明：将个股资金流向同步任务添加到定时任务列表
-- =====================================================

INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_by
) VALUES (
    'sync_moneyflow_stock_dc',
    'tasks.sync_moneyflow_stock_dc',
    '个股资金流向数据（DC）',
    '30 17 * * 1-5',
    false,
    '{}'::jsonb,
    'system'
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    updated_at = CURRENT_TIMESTAMP;

-- 输出添加完成信息
DO $$
BEGIN
    RAISE NOTICE '个股资金流向（DC）定时任务已添加到 scheduled_tasks 表';
END $$;
