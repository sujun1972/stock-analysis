-- =====================================================
-- 插入数据质量监控定时任务配置
-- 创建时间：2024-03
-- 说明：配置数据质量监控和报告生成的定时任务
-- =====================================================

-- 每日质量报告生成（每日7:00）
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
    'generate_daily_quality_report',
    'quality.generate_daily_report',
    '生成每日数据质量报告',
    '0 7 * * *',
    true,
    '{"export_html": true, "send_notification": true, "priority": "P1"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 周度质量报告生成（每周一8:00）
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
    'generate_weekly_quality_report',
    'quality.generate_weekly_report',
    '生成周度数据质量趋势报告',
    '0 8 * * 1',
    true,
    '{"include_trends": true, "compare_weeks": 4, "priority": "P2"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 实时质量检查（每小时执行）
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
    'real_time_quality_check',
    'quality.real_time_check',
    '实时数据质量检查，发现异常立即告警',
    '0 * * * *',
    true,
    '{"check_latest_data": true, "alert_threshold": 0.95, "priority": "P0"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 数据完整性检查（每日凌晨2:00）
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
    'data_integrity_check',
    'quality.integrity_check',
    '检查数据完整性，修复缺失数据',
    '0 2 * * *',
    true,
    '{"check_missing": true, "auto_repair": false, "priority": "P2"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 质量趋势分析（每日20:00）
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
    'quality_trend_analysis',
    'quality.trend_analysis',
    '分析数据质量趋势，预测潜在问题',
    '0 20 * * *',
    true,
    '{"analysis_days": 30, "predict_issues": true, "priority": "P2"}',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT (task_name) DO UPDATE SET
    module = EXCLUDED.module,
    description = EXCLUDED.description,
    cron_expression = EXCLUDED.cron_expression,
    params = EXCLUDED.params,
    updated_at = CURRENT_TIMESTAMP;

-- 告警清理任务（每日凌晨3:00）
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
    'cleanup_old_alerts',
    'quality.cleanup_alerts',
    '清理过期的质量告警记录',
    '0 3 * * *',
    false,  -- 默认关闭，需要手动启用
    '{"keep_days": 30, "archive": true, "priority": "P3"}',
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
    RAISE NOTICE '数据质量监控任务配置已插入';
    RAISE NOTICE '已配置6个定时任务：';
    RAISE NOTICE '  - 每日质量报告（已启用，每日7:00）';
    RAISE NOTICE '  - 周度质量报告（已启用，每周一8:00）';
    RAISE NOTICE '  - 实时质量检查（已启用，每小时）';
    RAISE NOTICE '  - 数据完整性检查（已启用，每日2:00）';
    RAISE NOTICE '  - 质量趋势分析（已启用，每日20:00）';
    RAISE NOTICE '  - 告警清理（已禁用，每日3:00）';
END $$;