-- 补充特色数据分类下缺少的 7 个定时任务
-- 已有：卖方盈利预测(400)、中央结算系统持股汇总(403)、神奇九转指标(408)、AH股比价(409)、机构调研表(410)
-- 新增：每日筹码及胜率(401)、每日筹码分布(402)、中央结算系统持股明细(404)、
--       沪深港股通持股明细(405)、股票开盘集合竞价(406)、股票收盘集合竞价(407)、券商每月荐股(411)

INSERT INTO scheduled_tasks (task_name, module, display_name, description, category, display_order, points_consumption, cron_expression, enabled, params)
VALUES
    (
        'tasks.sync_cyq_perf',
        'tasks.sync_cyq_perf',
        '每日筹码及胜率',
        '获取A股每日筹码平均成本和胜率情况，数据从2018年开始，每天18-19点更新（5000积分/天20000次，单次最大5000条）',
        '特色数据',
        401,
        5000,
        '0 19 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_cyq_chips',
        'tasks.sync_cyq_chips',
        '每日筹码分布',
        '获取A股每日的筹码分布情况，提供各价位占比，数据从2018年开始，每天18-19点更新（5000积分/天20000次，单次最大2000条）',
        '特色数据',
        402,
        5000,
        '30 19 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_ccass_hold_detail',
        'tasks.sync_ccass_hold_detail',
        '中央结算系统持股明细',
        '获取中央结算系统机构席位持股明细数据，当日数据在下一交易日早上9点前完成（8000积分/次，单次最大6000条）',
        '特色数据',
        404,
        8000,
        '0 9 * * 2-6',
        true,
        '{}'
    ),
    (
        'tasks.sync_hk_hold',
        'tasks.sync_hk_hold',
        '沪深港股通持股明细',
        '获取沪深港股通持股明细数据，注意：2024年8月20日起改为季度披露（2000积分/次）',
        '特色数据',
        405,
        2000,
        '0 10 * * 2-6',
        true,
        '{}'
    ),
    (
        'tasks.sync_stk_auction_o',
        'tasks.sync_stk_auction_o',
        '股票开盘集合竞价',
        '获取股票开盘9:30集合竞价数据，每天盘后更新，单次最大10000行（需要开通股票分钟权限）',
        '特色数据',
        406,
        NULL,
        '0 17 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_stk_auction_c',
        'tasks.sync_stk_auction_c',
        '股票收盘集合竞价',
        '股票收盘15:00集合竞价数据，每天盘后更新（需要开通股票分钟权限）',
        '特色数据',
        407,
        NULL,
        '30 17 * * 1-5',
        true,
        '{}'
    ),
    (
        'tasks.sync_broker_recommend',
        'tasks.sync_broker_recommend',
        '券商每月荐股',
        '获取券商月度金股推荐数据，一般在每月1-3日内更新当月数据（6000积分/次，单次最大1000行）',
        '特色数据',
        411,
        6000,
        '0 8 3 * *',
        true,
        '{}'
    )
ON CONFLICT DO NOTHING;
