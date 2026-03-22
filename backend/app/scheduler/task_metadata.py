"""
任务元数据配置
包含所有定时任务的完整元数据：名称、描述、分类、显示顺序、积分消耗等

设计原则：
- 单一数据源：所有任务元数据集中管理
- 结构化配置：使用字典结构便于查询和扩展
- 分类清晰：按业务领域分组，便于维护
"""

from datetime import datetime
from typing import Dict, Any


# ============================================
# 任务元数据映射表
# ============================================
# 格式说明：
# {
#     'module_name': {
#         'task': 'celery.task.name',           # Celery任务名称
#         'name': '任务显示名称',                  # 前端显示的名称
#         'description': '任务详细描述',          # 任务功能说明
#         'category': '任务分类',                 # 任务所属分类
#         'display_order': 100,                  # 显示排序号（数字越小越靠前）
#         'default_params': {...},               # 默认参数（可选）
#     }
# }

TASK_MAPPING: Dict[str, Dict[str, Any]] = {
    # ============================================
    # 基础数据同步任务（display_order: 100-199）
    # ============================================
    'stock_list': {
        'task': 'sync.stock_list',
        'name': '每日股票列表',
        'description': '每日同步A股所有股票的基础信息',
        'category': '基础数据',
        'display_order': 100
    },
    'new_stocks': {
        'task': 'sync.new_stocks',
        'name': '每日新股同步',
        'description': '同步最近上市的新股信息',
        'category': '基础数据',
        'display_order': 110,
        'default_params': {'days': 30}
    },
    'delisted_stocks': {
        'task': 'sync.delisted_stocks',
        'name': '每周退市同步',
        'description': '同步退市股票列表',
        'category': '基础数据',
        'display_order': 120
    },
    'concept': {
        'task': 'sync.concept',
        'name': '概念板块同步',
        'description': '同步概念板块分类信息',
        'category': '基础数据',
        'display_order': 130
    },

    # ============================================
    # 行情数据同步任务（display_order: 200-299）
    # ============================================
    'daily': {
        'task': 'sync.daily_batch',
        'name': '每日行情同步',
        'description': '同步股票日K线数据',
        'category': '行情数据',
        'display_order': 200,
        'default_params': {'years': 1}
    },

    # ============================================
    # 扩展数据同步任务（display_order: 300-399）
    # ============================================
    'extended.sync_daily_basic': {
        'task': 'extended.sync_daily_basic',
        'name': '每日指标同步',
        'description': '同步市盈率、市净率等每日指标数据',
        'category': '扩展数据',
        'display_order': 300
    },
    'extended.sync_moneyflow': {
        'task': 'extended.sync_moneyflow',
        'name': '资金流向同步（旧版）',
        'description': '同步个股资金流向数据（已废弃，建议使用Tushare或DC版本）',
        'category': '扩展数据',
        'display_order': 399
    },
    'tasks.sync_moneyflow': {
        'task': 'tasks.sync_moneyflow',
        'name': '个股资金流向（Tushare）',
        'description': '同步个股资金流向数据（Tushare标准接口，2000积分/次）',
        'category': '扩展数据',
        'display_order': 310
    },
    'tasks.sync_moneyflow_hsgt': {
        'task': 'tasks.sync_moneyflow_hsgt',
        'name': '沪深港通资金流向',
        'description': '同步沪深港通资金流向数据（北向+南向，2000积分/次）',
        'category': '扩展数据',
        'display_order': 320
    },
    'tasks.sync_moneyflow_mkt_dc': {
        'task': 'tasks.sync_moneyflow_mkt_dc',
        'name': '大盘资金流向（DC）',
        'description': '同步大盘资金流向数据（东方财富DC，120积分/次）',
        'category': '扩展数据',
        'display_order': 330
    },
    'tasks.sync_moneyflow_ind_dc': {
        'task': 'tasks.sync_moneyflow_ind_dc',
        'name': '板块资金流向（DC）',
        'description': '同步板块资金流向数据（东方财富DC，6000积分/次）',
        'category': '扩展数据',
        'display_order': 340
    },
    'tasks.sync_moneyflow_stock_dc': {
        'task': 'tasks.sync_moneyflow_stock_dc',
        'name': '个股资金流向（DC）',
        'description': '同步个股资金流向数据（东方财富DC，5000积分/次）',
        'category': '扩展数据',
        'display_order': 350
    },
    'tasks.sync_margin': {
        'task': 'tasks.sync_margin',
        'name': '融资融券交易汇总',
        'description': '同步交易所融资融券交易汇总数据（按交易所统计）',
        'category': '两融及转融通',
        'display_order': 510
    },
    'tasks.sync_margin_detail': {
        'task': 'tasks.sync_margin_detail',
        'name': '融资融券交易明细',
        'description': '同步个股融资融券交易明细数据（2000积分/次，单次最大6000行）',
        'category': '两融及转融通',
        'display_order': 515
    },
    'sync_margin_secs': {
        'task': 'extended.sync_margin_secs',
        'name': '融资融券标的（盘前更新）',
        'description': '同步沪深京三大交易所融资融券标的（包括ETF），每天盘前更新（2000积分/次）',
        'category': '两融及转融通',
        'display_order': 520
    },
    'tasks.sync_slb_len': {
        'task': 'tasks.sync_slb_len',
        'name': '转融资交易汇总',
        'description': '同步转融通融资汇总数据（期初余额、竞价成交、再借成交、偿还、期末余额）（2000积分/分钟200次，5000积分500次，单次最大5000行）',
        'category': '两融及转融通',
        'display_order': 525,
        'points_consumption': 2000
    },
    'extended.sync_margin': {
        'task': 'extended.sync_margin',
        'name': '融资融券明细（个股-旧版）',
        'description': '同步个股融资融券余额和明细数据（已废弃，建议使用新版）',
        'category': '两融及转融通',
        'display_order': 530
    },
    'extended.sync_stk_limit': {
        'task': 'extended.sync_stk_limit',
        'name': '涨跌停价格同步',
        'description': '同步股票涨跌停价格信息',
        'category': '扩展数据',
        'display_order': 370
    },
    'extended.sync_block_trade': {
        'task': 'extended.sync_block_trade',
        'name': '大宗交易同步',
        'description': '同步大宗交易明细数据',
        'category': '扩展数据',
        'display_order': 380
    },
    'extended.sync_adj_factor': {
        'task': 'extended.sync_adj_factor',
        'name': '复权因子同步',
        'description': '同步股票复权因子数据',
        'category': '扩展数据',
        'display_order': 385
    },
    'extended.sync_suspend': {
        'task': 'extended.sync_suspend',
        'name': '停复牌信息同步',
        'description': '同步股票停复牌公告',
        'category': '扩展数据',
        'display_order': 390
    },

    # ============================================
    # 特色数据任务（display_order: 400-449）
    # ============================================
    'tasks.sync_report_rc': {
        'task': 'tasks.sync_report_rc',
        'name': '卖方盈利预测数据',
        'description': '获取券商（卖方）每天研报的盈利预测数据，数据从2010年开始（120积分试用，8000积分正式权限）',
        'category': '特色数据',
        'display_order': 400,
        'points_consumption': 8000,
        'default_params': {'report_date': None}
    },

    # ============================================
    # 参考数据任务（display_order: 450-499）
    # ============================================
    'tasks.sync_stk_shock': {
        'task': 'tasks.sync_stk_shock',
        'name': '个股异常波动',
        'description': '根据证券交易所交易规则的有关规定，交易所每日发布股票交易异常波动情况（6000积分/次，单次最大1000行）',
        'category': '参考数据',
        'display_order': 450,
        'points_consumption': 6000,
        'default_params': {'trade_date': None, 'start_date': None, 'end_date': None}
    },
    'tasks.sync_stk_alert': {
        'task': 'tasks.sync_stk_alert',
        'name': '交易所重点提示证券',
        'description': '根据证券交易所交易规则的有关规定，交易所每日发布重点提示证券（6000积分/次，单次最大1000行）',
        'category': '参考数据',
        'display_order': 451,
        'points_consumption': 6000,
        'default_params': {'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_stk_high_shock': {
        'task': 'tasks.sync_stk_high_shock',
        'name': '个股严重异常波动',
        'description': '根据证券交易所交易规则的有关规定，交易所每日发布股票交易严重异常波动情况（6000积分/次，单次最大1000行）',
        'category': '参考数据',
        'display_order': 452,
        'points_consumption': 6000,
        'default_params': {'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_pledge_stat': {
        'task': 'tasks.sync_pledge_stat',
        'name': '股权质押统计',
        'description': '获取股票质押统计数据，包括质押次数、无限售/限售股质押数量、总股本、质押比例等（500积分/次，单次最大1000行）',
        'category': '参考数据',
        'display_order': 453,
        'points_consumption': 500,
        'default_params': {'trade_date': None, 'ts_code': None}
    },

    'tasks.sync_repurchase': {
        'task': 'tasks.sync_repurchase',
        'name': '股票回购',
        'description': '获取上市公司回购股票数据，包括回购公告日期、回购进度、回购数量、回购金额、回购价格区间等（600积分/次）',
        'category': '参考数据',
        'display_order': 454,
        'points_consumption': 600,
        'default_params': {'ann_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_share_float': {
        'task': 'tasks.sync_share_float',
        'name': '限售股解禁',
        'description': '获取限售股解禁数据，包括公告日期、解禁日期、流通股份、流通比率、股东名称、股份类型等（120积分/次，单次最大6000行）',
        'category': '参考数据',
        'display_order': 455,
        'points_consumption': 120,
        'default_params': {'ts_code': None, 'ann_date': None, 'float_date': None, 'start_date': None, 'end_date': None}
    },

    # ============================================
    # 打板专题任务（display_order: 550-599）
    # ============================================
    'top_list': {
        'task': 'tasks.sync_top_list',
        'name': '龙虎榜每日明细',
        'description': '同步龙虎榜每日交易明细数据（涨跌幅偏离值达7%、连续涨跌、换手率达20%等上榜股票及席位信息）（2000积分/次，单次最大10000行）',
        'category': '打板专题',
        'display_order': 550,
        'points_consumption': 2000,
        'default_params': {'trade_date': None}
    },

    'top_inst': {
        'task': 'tasks.sync_top_inst',
        'name': '龙虎榜机构明细',
        'description': '同步龙虎榜机构成交明细数据（营业部名称、买卖类型、买入额、卖出额、净成交额等）（5000积分/次，单次最大10000行）',
        'category': '打板专题',
        'display_order': 551,
        'points_consumption': 5000,
        'default_params': {'trade_date': None}
    },
    'limit_list': {
        'task': 'tasks.sync_limit_list',
        'name': '涨跌停列表',
        'description': '同步每日涨跌停、炸板数据（包含行情数据、封板数据、连板统计等）（5000积分/次，单次最大2500行，数据从2020年开始）',
        'category': '打板专题',
        'display_order': 552,
        'points_consumption': 5000,
        'default_params': {'trade_date': None, 'limit_type': None}
    },
    'limit_step': {
        'task': 'tasks.sync_limit_step',
        'name': '连板天梯',
        'description': '同步每天连板个数晋级的股票，可以分析出每天连续涨停进阶个数，判断强势热度（8000积分以上每分钟500次，单次最大2000行）',
        'category': '打板专题',
        'display_order': 553,
        'points_consumption': 8000,
        'default_params': {'trade_date': None, 'nums': None}
    },
    'limit_cpt': {
        'task': 'tasks.sync_limit_cpt',
        'name': '最强板块统计',
        'description': '获取每天涨停股票最多最强的概念板块，可以分析强势板块的轮动，判断资金动向（8000积分以上每分钟500次，单次最大2000行）',
        'category': '打板专题',
        'display_order': 554,
        'points_consumption': 8000,
        'default_params': {'trade_date': None, 'ts_code': None}
    },

    # ============================================
    # 市场情绪任务（display_order: 600-699）
    # ============================================
    'sentiment': {
        'task': 'sentiment.daily_sync_17_30',
        'name': '市场情绪抓取',
        'description': '市场情绪数据抓取（17:30）- 包含交易日历、涨停板池、龙虎榜',
        'category': '市场情绪',
        'display_order': 600
    },
    'sentiment.ai_analysis': {
        'task': 'sentiment.ai_analysis_18_00',
        'name': '情绪AI分析',
        'description': '市场情绪AI分析（18:00）- 基于17:30数据生成盘后分析报告',
        'category': '市场情绪',
        'display_order': 610
    },
    'sentiment.manual_sync': {
        'task': 'sentiment.manual_sync',
        'name': '手动情绪同步',
        'description': '手动触发情绪数据同步',
        'category': '市场情绪',
        'display_order': 620,
        'default_params': {'date': None}
    },
    'sentiment.batch_sync': {
        'task': 'sentiment.batch_sync',
        'name': '批量情绪同步',
        'description': '批量同步历史情绪数据',
        'category': '市场情绪',
        'display_order': 630
    },
    'sentiment.calendar_sync': {
        'task': 'sentiment.calendar_sync',
        'name': '交易日历同步',
        'description': '同步股市交易日历',
        'category': '市场情绪',
        'display_order': 640,
        'default_params': {'years': [datetime.now().year]}
    },

    # ============================================
    # 盘前分析任务（display_order: 700-799）
    # ============================================
    'premarket': {
        'task': 'premarket.full_workflow_8_00',
        'name': '盘前预期分析',
        'description': '盘前预期管理系统(8:00) - 抓取外盘数据+过滤新闻+AI分析',
        'category': '盘前分析',
        'display_order': 700
    },
    'premarket.sync_data': {
        'task': 'premarket.sync_data_only',
        'name': '盘前数据同步',
        'description': '同步盘前所需的各项数据',
        'category': '盘前分析',
        'display_order': 710
    },
    'premarket.generate_analysis': {
        'task': 'premarket.generate_analysis_only',
        'name': '生成AI分析',
        'description': '生成盘前AI分析报告',
        'category': '盘前分析',
        'display_order': 720
    },

    # ============================================
    # 质量监控任务（display_order: 800-899）
    # ============================================
    'quality.daily_report': {
        'task': 'app.tasks.quality_tasks.generate_daily_quality_report',
        'name': '每日质量报告',
        'description': '生成每日数据质量报告',
        'category': '质量监控',
        'display_order': 800
    },
    'quality.weekly_report': {
        'task': 'app.tasks.quality_tasks.generate_weekly_quality_report',
        'name': '周度质量报告',
        'description': '生成周度数据质量趋势报告',
        'category': '质量监控',
        'display_order': 810
    },
    'quality.real_time_check': {
        'task': 'app.tasks.quality_tasks.real_time_quality_check',
        'name': '实时质量检查',
        'description': '实时数据质量检查，发现异常立即告警',
        'category': '质量监控',
        'display_order': 820
    },
    'quality.integrity_check': {
        'task': 'app.tasks.quality_tasks.data_integrity_check',
        'name': '数据完整性检查',
        'description': '检查数据完整性，修复缺失数据',
        'category': '质量监控',
        'display_order': 830
    },
    'quality.trend_analysis': {
        'task': 'app.tasks.quality_tasks.quality_trend_analysis',
        'name': '质量趋势分析',
        'description': '分析数据质量趋势，预测潜在问题',
        'category': '质量监控',
        'display_order': 840
    },
    'quality.cleanup_alerts': {
        'task': 'app.tasks.quality_tasks.cleanup_old_alerts',
        'name': '清理过期告警',
        'description': '清理过期的质量告警记录',
        'category': '质量监控',
        'display_order': 850
    },

    # ============================================
    # 报告通知任务（display_order: 900-999）
    # ============================================
    'notification.send_email': {
        'task': 'app.tasks.notification_tasks.send_email_notification',
        'name': '邮件通知',
        'description': '发送邮件通知',
        'category': '报告通知',
        'display_order': 900
    },
    'notification.send_telegram': {
        'task': 'app.tasks.notification_tasks.send_telegram_notification',
        'name': 'Telegram通知',
        'description': '发送Telegram消息通知',
        'category': '报告通知',
        'display_order': 910
    },
    'notification.cleanup': {
        'task': 'app.tasks.notification_tasks.cleanup_expired_notifications',
        'name': '清理过期通知',
        'description': '清理过期的通知记录',
        'category': '报告通知',
        'display_order': 920
    },
    'notification.health_check': {
        'task': 'app.tasks.notification_tasks.notification_health_check',
        'name': '通知系统健康检查',
        'description': '检查通知系统运行状态',
        'category': '报告通知',
        'display_order': 930
    }
}


# ============================================
# 任务分类定义
# ============================================
TASK_CATEGORIES = [
    {'name': '基础数据', 'order': 1},
    {'name': '行情数据', 'order': 2},
    {'name': '扩展数据', 'order': 3},
    {'name': '资金流向', 'order': 4},
    {'name': '两融及转融通', 'order': 5},
    {'name': '特色数据', 'order': 6},
    {'name': '打板专题', 'order': 7},
    {'name': '市场情绪', 'order': 8},
    {'name': '盘前分析', 'order': 9},
    {'name': '质量监控', 'order': 10},
    {'name': '报告通知', 'order': 11},
    {'name': '系统维护', 'order': 12}
]


# ============================================
# 元数据字段定义
# ============================================
# 用于过滤任务执行参数的元数据字段
METADATA_FIELDS = {
    'priority',           # 任务优先级
    'points_consumption', # Tushare积分消耗
    'retry_count',        # 重试次数
    'timeout'             # 超时时间
}
