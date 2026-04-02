-- 新增 ST股票列表 和 交易日历 定时任务
-- 对应 task_metadata.py 中已有的 tasks.sync_stock_st 和 tasks.sync_trade_cal

INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES
    (
        'tasks.sync_stock_st',
        'tasks.sync_stock_st',
        'ST股票列表',
        '获取ST股票列表，可根据交易日期获取历史上每天的ST列表',
        '基础数据',
        140,
        3000,
        '30 16 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_trade_cal',
        'tasks.sync_trade_cal',
        '交易日历',
        '获取各大交易所交易日历数据，默认同步上交所(SSE)和深交所(SZSE)，支持指定交易所和日期范围',
        '基础数据',
        120,
        2000,
        '0 2 1 * *',
        true,
        '{}'
    )
ON CONFLICT DO NOTHING;
