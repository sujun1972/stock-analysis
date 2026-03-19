-- =====================================================
-- 插入扩展数据同步定时任务配置
-- 创建时间：2024-03
-- 说明：配置Tushare扩展数据的定时同步任务
-- =====================================================

-- 每日指标同步（每日17:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_daily_basic',
    'extended.sync_daily_basic',
    '同步每日指标数据（换手率、PE等）',
    '0 17 * * *',
    true,
    '{"points_consumption": 120, "priority": "P0"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 资金流向同步（每日17:30，默认关闭）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_moneyflow',
    'extended.sync_moneyflow',
    '同步资金流向数据（高积分消耗，谨慎使用）',
    '30 17 * * *',
    false,  -- 默认关闭，因为积分消耗高
    '{"points_consumption": 2000, "strategy": "top100", "priority": "P0"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 北向资金同步（每日18:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_hk_hold',
    'extended.sync_hk_hold',
    '同步北向资金持股数据',
    '0 18 * * *',
    true,
    '{"points_consumption": 300, "priority": "P1"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 融资融券同步（每日18:30）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_margin',
    'extended.sync_margin',
    '同步融资融券数据',
    '30 18 * * *',
    true,
    '{"points_consumption": 300, "priority": "P2"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 涨跌停价格同步（每日9:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_stk_limit',
    'extended.sync_stk_limit',
    '同步涨跌停价格数据',
    '0 9 * * *',
    true,
    '{"points_consumption": 120, "priority": "P1"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 复权因子同步（每周一2:00）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_adj_factor',
    'extended.sync_adj_factor',
    '同步复权因子',
    '0 2 * * 1',
    true,
    '{"points_consumption": 120, "priority": "P2"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 大宗交易同步（每日19:00，默认关闭）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_block_trade',
    'extended.sync_block_trade',
    '同步大宗交易数据',
    '0 19 * * *',
    false,  -- 默认关闭
    '{"points_consumption": 300, "priority": "P3"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 停复牌信息同步（每日8:30）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_suspend',
    'extended.sync_suspend',
    '同步停复牌信息',
    '30 8 * * *',
    false,  -- 默认关闭
    '{"points_consumption": 120, "priority": "P3"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 沪深港通资金流向同步（每日17:30）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_moneyflow_hsgt',
    'moneyflow_hsgt',
    '同步沪深港通资金流向数据（北向+南向资金）',
    '30 17 * * *',
    true,
    '{"points_consumption": 2000, "priority": "P0"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 大盘资金流向同步（每日17:45）
INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_at,
    updated_at
) VALUES (
    'sync_moneyflow_mkt_dc',
    'moneyflow_mkt_dc',
    '同步大盘资金流向数据（东方财富DC）',
    '45 17 * * *',
    true,
    '{"points_consumption": 120, "priority": "P1"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 输出插入完成信息
DO $$
BEGIN
    RAISE NOTICE '扩展数据同步任务配置已插入';
    RAISE NOTICE '已配置10个定时任务：';
    RAISE NOTICE '  - 每日指标（已启用，120积分）';
    RAISE NOTICE '  - 资金流向（已禁用，2000积分）';
    RAISE NOTICE '  - 北向资金（已启用，300积分）';
    RAISE NOTICE '  - 融资融券（已启用，300积分）';
    RAISE NOTICE '  - 涨跌停价格（已启用，120积分）';
    RAISE NOTICE '  - 复权因子（已启用，120积分）';
    RAISE NOTICE '  - 大宗交易（已禁用，300积分）';
    RAISE NOTICE '  - 停复牌信息（已禁用，120积分）';
    RAISE NOTICE '  - 沪深港通资金流向（已启用，2000积分）';
    RAISE NOTICE '  - 大盘资金流向（已启用，120积分）';
END $$;