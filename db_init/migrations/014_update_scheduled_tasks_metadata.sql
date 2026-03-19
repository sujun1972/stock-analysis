-- 批量更新 scheduled_tasks 表的元数据字段
-- 根据 TaskExecutor.TASK_MAPPING 中的配置更新现有任务的友好名称、描述、分类和排序

-- ============================================
-- 基础数据同步任务（display_order: 100-199）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '每日股票列表',
    description = '每日同步A股所有股票的基础信息',
    category = '基础数据',
    display_order = 100
WHERE module = 'stock_list' OR task_name = 'daily_stock_list_sync';

UPDATE scheduled_tasks
SET display_name = '每日新股同步',
    description = '同步最近上市的新股信息',
    category = '基础数据',
    display_order = 110
WHERE module = 'new_stocks' OR task_name = 'daily_new_stocks_sync';

UPDATE scheduled_tasks
SET display_name = '每周退市同步',
    description = '同步退市股票列表',
    category = '基础数据',
    display_order = 120
WHERE module = 'delisted_stocks' OR task_name = 'weekly_delisted_stocks_sync';

UPDATE scheduled_tasks
SET display_name = '概念板块同步',
    description = '同步概念板块分类信息',
    category = '基础数据',
    display_order = 130
WHERE module = 'concept';

-- ============================================
-- 行情数据同步任务（display_order: 200-299）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '每日行情同步',
    description = '同步股票日K线数据',
    category = '行情数据',
    display_order = 200
WHERE module = 'daily' OR task_name = 'daily_data_sync' OR task_name = 'sync_daily_batch';

UPDATE scheduled_tasks
SET display_name = '分钟数据同步',
    description = '同步股票的分钟级K线数据',
    category = '行情数据',
    display_order = 210
WHERE module = 'minute' OR task_name = 'sync_minute_data';

UPDATE scheduled_tasks
SET display_name = '实时行情同步',
    description = '同步股票的实时报价数据',
    category = '行情数据',
    display_order = 220
WHERE module = 'realtime' OR task_name = 'sync_realtime_quotes';

-- ============================================
-- 扩展数据同步任务（display_order: 300-399）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '每日指标同步',
    description = '同步市盈率、市净率等每日指标数据',
    category = '扩展数据',
    display_order = 300
WHERE module = 'extended.sync_daily_basic' OR task_name = 'sync_daily_basic';

UPDATE scheduled_tasks
SET display_name = '个股资金流向（Tushare）',
    description = '同步个股资金流向数据（Tushare标准接口，2000积分/次）',
    category = '扩展数据',
    display_order = 310
WHERE module = 'tasks.sync_moneyflow' OR task_name = 'sync_moneyflow';

UPDATE scheduled_tasks
SET display_name = '沪深港通资金流向',
    description = '同步沪深港通资金流向数据（北向+南向，2000积分/次）',
    category = '扩展数据',
    display_order = 320
WHERE module = 'tasks.sync_moneyflow_hsgt' OR task_name = 'sync_moneyflow_hsgt';

UPDATE scheduled_tasks
SET display_name = '大盘资金流向（DC）',
    description = '同步大盘资金流向数据（东方财富DC，120积分/次）',
    category = '扩展数据',
    display_order = 330
WHERE module = 'tasks.sync_moneyflow_mkt_dc' OR task_name = 'sync_moneyflow_mkt_dc';

UPDATE scheduled_tasks
SET display_name = '板块资金流向（DC）',
    description = '同步板块资金流向数据（东方财富DC，6000积分/次）',
    category = '扩展数据',
    display_order = 340
WHERE module = 'tasks.sync_moneyflow_ind_dc' OR task_name = 'sync_moneyflow_ind_dc';

UPDATE scheduled_tasks
SET display_name = '个股资金流向（DC）',
    description = '同步个股资金流向数据（东方财富DC，5000积分/次）',
    category = '扩展数据',
    display_order = 350
WHERE module = 'tasks.sync_moneyflow_stock_dc' OR task_name = 'sync_moneyflow_stock_dc';

UPDATE scheduled_tasks
SET display_name = '融资融券同步',
    description = '同步两融余额和明细数据',
    category = '扩展数据',
    display_order = 360
WHERE module = 'extended.sync_margin' OR task_name = 'sync_margin';

UPDATE scheduled_tasks
SET display_name = '涨跌停价格同步',
    description = '同步股票涨跌停价格信息',
    category = '扩展数据',
    display_order = 370
WHERE module = 'extended.sync_stk_limit' OR task_name = 'sync_stk_limit';

UPDATE scheduled_tasks
SET display_name = '大宗交易同步',
    description = '同步大宗交易明细数据',
    category = '扩展数据',
    display_order = 380
WHERE module = 'extended.sync_block_trade' OR task_name = 'sync_block_trade';

UPDATE scheduled_tasks
SET display_name = '复权因子同步',
    description = '同步股票复权因子数据',
    category = '扩展数据',
    display_order = 385
WHERE module = 'extended.sync_adj_factor' OR task_name = 'sync_adj_factor';

UPDATE scheduled_tasks
SET display_name = '停复牌信息同步',
    description = '同步股票停复牌公告',
    category = '扩展数据',
    display_order = 390
WHERE module = 'extended.sync_suspend' OR task_name = 'sync_suspend';

UPDATE scheduled_tasks
SET display_name = '资金流向同步（旧版）',
    description = '同步个股资金流向数据（已废弃，建议使用Tushare或DC版本）',
    category = '扩展数据',
    display_order = 399
WHERE module = 'extended.sync_moneyflow';

-- ============================================
-- 市场情绪任务（display_order: 400-499）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '市场情绪抓取',
    description = '市场情绪数据抓取（17:30）- 包含交易日历、涨停板池、龙虎榜',
    category = '市场情绪',
    display_order = 400
WHERE module = 'sentiment' OR task_name = 'daily_sentiment_sync';

UPDATE scheduled_tasks
SET display_name = '情绪AI分析',
    description = '市场情绪AI分析（18:00）- 基于17:30数据生成盘后分析报告',
    category = '市场情绪',
    display_order = 410
WHERE module = 'sentiment.ai_analysis' OR task_name = 'sentiment.ai_analysis_18_00' OR task_name = 'daily_sentiment_ai_analysis';

UPDATE scheduled_tasks
SET display_name = '手动情绪同步',
    description = '手动触发情绪数据同步',
    category = '市场情绪',
    display_order = 420
WHERE module = 'sentiment.manual_sync' OR task_name = 'manual_sentiment_sync';

UPDATE scheduled_tasks
SET display_name = '批量情绪同步',
    description = '批量同步历史情绪数据',
    category = '市场情绪',
    display_order = 430
WHERE module = 'sentiment.batch_sync' OR task_name = 'batch_sentiment_sync';

UPDATE scheduled_tasks
SET display_name = '交易日历同步',
    description = '同步股市交易日历',
    category = '市场情绪',
    display_order = 440
WHERE module = 'sentiment.calendar_sync' OR task_name = 'sync_trading_calendar';

-- ============================================
-- 盘前分析任务（display_order: 500-599）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '盘前预期分析',
    description = '盘前预期管理系统(8:00) - 抓取外盘数据+过滤新闻+AI分析',
    category = '盘前分析',
    display_order = 500
WHERE module = 'premarket' OR task_name = 'premarket_expectation_8_00' OR task_name = 'premarket_full_workflow';

UPDATE scheduled_tasks
SET display_name = '盘前数据同步',
    description = '同步盘前所需的各项数据',
    category = '盘前分析',
    display_order = 510
WHERE module = 'premarket.sync_data' OR task_name = 'sync_premarket_data';

UPDATE scheduled_tasks
SET display_name = '生成AI分析',
    description = '生成盘前AI分析报告',
    category = '盘前分析',
    display_order = 520
WHERE module = 'premarket.generate_analysis' OR task_name = 'generate_analysis';

-- ============================================
-- 质量监控任务（display_order: 600-699）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '每日质量报告',
    description = '生成每日数据质量报告',
    category = '质量监控',
    display_order = 600
WHERE module = 'quality.daily_report' OR task_name = 'generate_daily_quality_report';

UPDATE scheduled_tasks
SET display_name = '周度质量报告',
    description = '生成周度数据质量趋势报告',
    category = '质量监控',
    display_order = 610
WHERE module = 'quality.weekly_report' OR task_name = 'generate_weekly_quality_report';

UPDATE scheduled_tasks
SET display_name = '实时质量检查',
    description = '实时数据质量检查，发现异常立即告警',
    category = '质量监控',
    display_order = 620
WHERE module = 'quality.real_time_check' OR task_name = 'real_time_quality_check';

UPDATE scheduled_tasks
SET display_name = '数据完整性检查',
    description = '检查数据完整性，修复缺失数据',
    category = '质量监控',
    display_order = 630
WHERE module = 'quality.integrity_check' OR task_name = 'data_integrity_check';

UPDATE scheduled_tasks
SET display_name = '质量趋势分析',
    description = '分析数据质量趋势，预测潜在问题',
    category = '质量监控',
    display_order = 640
WHERE module = 'quality.trend_analysis' OR task_name = 'quality_trend_analysis';

UPDATE scheduled_tasks
SET display_name = '清理过期告警',
    description = '清理过期的质量告警记录',
    category = '质量监控',
    display_order = 650
WHERE module = 'quality.cleanup_alerts' OR task_name = 'cleanup_old_alerts';

-- ============================================
-- 报告通知任务（display_order: 700-799）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '每日市场报告',
    description = '生成每日市场分析报告',
    category = '报告通知',
    display_order = 700
WHERE task_name = 'generate_daily_report';

UPDATE scheduled_tasks
SET display_name = '邮件通知',
    description = '发送邮件通知',
    category = '报告通知',
    display_order = 710
WHERE module = 'notification.send_email' OR task_name = 'send_email_notification';

UPDATE scheduled_tasks
SET display_name = 'Telegram通知',
    description = '发送Telegram消息通知',
    category = '报告通知',
    display_order = 720
WHERE module = 'notification.send_telegram' OR task_name = 'send_telegram_notification';

UPDATE scheduled_tasks
SET display_name = '定时报告通知',
    description = '定时发送报告通知',
    category = '报告通知',
    display_order = 730
WHERE task_name = 'schedule_report_notification';

UPDATE scheduled_tasks
SET display_name = '清理过期通知',
    description = '清理过期的通知记录',
    category = '报告通知',
    display_order = 740
WHERE module = 'notification.cleanup' OR task_name = 'cleanup_expired_notifications';

UPDATE scheduled_tasks
SET display_name = '通知系统健康检查',
    description = '检查通知系统运行状态',
    category = '报告通知',
    display_order = 750
WHERE module = 'notification.health_check' OR task_name = 'notification_health_check';

-- ============================================
-- 系统维护任务（display_order: 800-899）
-- ============================================

UPDATE scheduled_tasks
SET display_name = '重置速率限制',
    description = '重置每日API调用速率限制',
    category = '系统维护',
    display_order = 800
WHERE task_name = 'reset_daily_rate_limits';

UPDATE scheduled_tasks
SET display_name = '数据库清理',
    description = '清理过期数据和优化表',
    category = '系统维护',
    display_order = 810
WHERE task_name = 'database_cleanup';

UPDATE scheduled_tasks
SET display_name = '数据库备份',
    description = '执行数据库备份任务',
    category = '系统维护',
    display_order = 820
WHERE task_name = 'backup_database';

-- ============================================
-- 处理没有匹配的任务（设置默认值）
-- ============================================

-- 将未分类的任务设置为"其他"分类，排序靠后
UPDATE scheduled_tasks
SET category = '其他',
    display_order = 9999
WHERE category IS NULL;

-- 如果 display_name 为空，使用 task_name 作为默认值
UPDATE scheduled_tasks
SET display_name = task_name
WHERE display_name IS NULL OR display_name = '';

-- 显示更新结果
SELECT
    category,
    COUNT(*) as task_count,
    STRING_AGG(display_name, ', ' ORDER BY display_order) as tasks
FROM scheduled_tasks
GROUP BY category
ORDER BY MIN(display_order);
