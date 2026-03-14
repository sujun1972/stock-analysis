-- ================================================
-- 定时任务默认配置数据
-- 将原有硬编码的定时任务迁移到数据库配置
-- ================================================

-- 清空现有的默认任务（如果存在）
DELETE FROM scheduled_tasks WHERE task_name IN (
    'daily_sentiment_sync',
    'daily_sentiment_ai_analysis',
    'daily_premarket_workflow',
    'daily_concept_sync'
);

-- 插入迁移后的定时任务配置
-- 注意：时间使用UTC时区

INSERT INTO scheduled_tasks (
    task_name,
    module,
    description,
    cron_expression,
    enabled,
    params,
    created_by
) VALUES
    -- 1. 每日17:30（北京时间）同步市场情绪数据
    -- UTC时间: 9:30 = 北京时间17:30
    (
        'daily_sentiment_sync',
        'sentiment',
        '每日市场情绪数据同步',
        '30 9 * * 1-5',  -- 分 时 日 月 周（周一到周五UTC 9:30）
        false,  -- 默认禁用，需要在Admin界面手动启用
        '{}',
        'system'
    ),

    -- 2. 每日18:00（北京时间）执行市场情绪AI分析
    -- UTC时间: 10:00 = 北京时间18:00
    (
        'daily_sentiment_ai_analysis',
        'sentiment_ai',
        '每日市场情绪AI智能分析',
        '0 10 * * 1-5',  -- 周一到周五UTC 10:00
        false,
        '{}',
        'system'
    ),

    -- 3. 每日8:00（北京时间）执行盘前完整工作流
    -- UTC时间: 0:00 = 北京时间8:00
    (
        'daily_premarket_workflow',
        'premarket',
        '每日盘前数据分析工作流',
        '0 0 * * 1-5',  -- 周一到周五UTC 0:00
        false,
        '{}',
        'system'
    ),

    -- 4. 每日凌晨2:00（北京时间）同步概念数据
    -- UTC时间: 18:00（前一天）= 北京时间2:00
    (
        'daily_concept_sync',
        'concept',
        '每日概念数据同步',
        '0 18 * * 0-4',  -- 周日到周四UTC 18:00（对应周一到周五北京时间2:00）
        false,
        '{"source": null}',
        'system'
    ),

    -- 5. 每日凌晨1:00（北京时间）同步股票列表
    (
        'daily_stock_list_sync',
        'stock_list',
        '每日股票列表同步',
        '0 17 * * *',  -- 每天UTC 17:00 = 北京时间1:00
        false,
        '{}',
        'system'
    ),

    -- 6. 每日凌晨2:00（北京时间）同步新股列表
    (
        'daily_new_stocks_sync',
        'new_stocks',
        '每日新股列表同步',
        '0 18 * * *',  -- 每天UTC 18:00 = 北京时间2:00
        false,
        '{"days": 30}',
        'system'
    ),

    -- 7. 每周日凌晨3:00（北京时间）同步退市列表
    (
        'weekly_delisted_stocks_sync',
        'delisted_stocks',
        '每周退市股票列表同步',
        '0 19 * * 0',  -- 每周日UTC 19:00 = 北京时间周一3:00
        false,
        '{}',
        'system'
    ),

    -- 8. 每日18:00（北京时间）批量同步日线数据
    (
        'daily_data_batch_sync',
        'daily',
        '每日批量同步日线数据',
        '0 10 * * 1-5',  -- 工作日UTC 10:00 = 北京时间18:00
        false,
        '{"max_stocks": 100}',
        'system'
    )
ON CONFLICT (task_name) DO UPDATE SET
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 完成
COMMENT ON TABLE scheduled_tasks IS '定时任务配置表（已迁移原有硬编码任务）';

-- 输出统计信息
SELECT
    COUNT(*) as total_tasks,
    COUNT(*) FILTER (WHERE enabled = true) as enabled_tasks,
    COUNT(*) FILTER (WHERE enabled = false) as disabled_tasks
FROM scheduled_tasks;
