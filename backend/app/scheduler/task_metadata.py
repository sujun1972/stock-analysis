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
        'default_params': {'days': 90}
    },
    'concept': {
        'task': 'sync.concept',
        'name': '概念板块同步',
        'description': '同步概念板块分类信息',
        'category': '基础数据',
        'display_order': 130
    },
    'tasks.sync_stock_st': {
        'task': 'tasks.sync_stock_st',
        'name': 'ST股票列表',
        'description': '获取ST股票列表，可根据交易日期获取历史上每天的ST列表',
        'category': '基础数据',
        'display_order': 140,
        'points_consumption': 3000
    },
    'tasks.sync_dc_member': {
        'task': 'tasks.sync_dc_member',
        'name': '东方财富板块成分',
        'description': '获取东方财富板块每日成分数据，可以根据概念板块代码和交易日期，获取历史成分',
        'category': '基础数据',
        'display_order': 150,
        'points_consumption': 6000
    },
    'tasks.sync_dc_index': {
        'task': 'tasks.sync_dc_index',
        'name': '东方财富板块数据',
        'description': '获取东方财富每个交易日的概念/行业/地域板块数据，支持按日期和板块类型查询',
        'category': '基础数据',
        'display_order': 155,
        'points_consumption': 6000
    },
    'tasks.sync_dc_daily': {
        'task': 'tasks.sync_dc_daily',
        'name': '东方财富概念板块行情',
        'description': '获取东方财富概念板块、行业指数板块、地域板块行情数据，历史数据从2020年开始',
        'category': '基础数据',
        'display_order': 160,
        'points_consumption': 6000
    },
    'tasks.sync_trade_cal': {
        'task': 'tasks.sync_trade_cal',
        'name': '交易日历',
        'description': '获取各大交易所交易日历数据，默认同步上交所(SSE)和深交所(SZSE)，支持指定交易所和日期范围',
        'category': '基础数据',
        'display_order': 120,
        'points_consumption': 2000
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

    'tasks.sync_daily_single': {
        'task': 'tasks.sync_daily_single',
        'name': '股票日线数据同步（单只）',
        'description': '同步单只股票日线数据。指定code同步历史数据，支持按年数或日期范围',
        'category': '行情数据',
        'display_order': 205,
        'points_consumption': 120,  # Tushare daily 接口
        'default_params': {'code': None, 'start_date': None, 'end_date': None, 'years': 5}
    },

    'tasks.sync_daily_recent_all': {
        'task': 'tasks.sync_daily_recent_all',
        'name': '全市场日线数据（近7日）',
        'description': '逐只同步全部上市股票最近7个交易日的日线数据，适合每日定时增量更新。替代原全市场模式（原全市场仅同步最近1个交易日）',
        'category': '行情数据',
        'display_order': 206,
        'points_consumption': 120,
        'default_params': {}
    },

    'tasks.sync_daily_full_history': {
        'task': 'tasks.sync_daily_full_history',
        'name': '日线数据全量历史同步',
        'description': '逐只同步全部上市股票自2021年1月1日起的全量日线数据，支持中断续继（跳过已同步股票）。首次执行或大规模补数据时使用',
        'category': '行情数据',
        'display_order': 207,
        'points_consumption': 120,
        'default_params': {}
    },

    'tasks.sync_suspend': {
        'task': 'tasks.sync_suspend',
        'name': '每日停复牌信息',
        'description': '按日期方式获取股票每日停复牌信息，包括停牌时间段、停复牌类型等（不定期更新）',
        'category': '行情数据',
        'display_order': 210,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None, 'suspend_type': None}
    },

    'tasks.sync_suspend_full_history': {
        'task': 'tasks.sync_suspend_full_history',
        'name': '停复牌全量历史同步',
        'description': '按周切片拉取自2005年起的全量停复牌历史数据，5并发，支持中断续继',
        'category': '行情数据',
        'display_order': 211,
        'default_params': {}
    },

    'tasks.sync_stk_limit_d': {
        'task': 'tasks.sync_stk_limit_d',
        'name': '每日涨跌停价格',
        'description': '获取全市场每日涨跌停价格，包括涨停价格、跌停价格等（每交易日8:40更新，2000积分/次，单次最大5800条）',
        'category': '行情数据',
        'display_order': 220,
        'points_consumption': 2000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },
    'tasks.sync_stk_limit_d_full_history': {
        'task': 'tasks.sync_stk_limit_d_full_history',
        'name': '每日涨跌停价格（全量）',
        'description': '逐只股票全量同步每日涨跌停价格历史数据，8并发，支持Redis中断续继，避免单次5800条上限',
        'category': '行情数据',
        'display_order': 221,
        'points_consumption': 2000,
        'default_params': {'start_date': None}
    },

    'tasks.sync_daily_basic': {
        'task': 'tasks.sync_daily_basic',
        'name': '每日指标',
        'description': '获取全部股票每日重要的基本面指标，可用于选股分析、报表展示等（2000积分/次，单次最大6000条）',
        'category': '行情数据',
        'display_order': 230,
        'points_consumption': 2000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },
    'tasks.sync_daily_basic_full_history': {
        'task': 'tasks.sync_daily_basic_full_history',
        'name': '每日指标（全量）',
        'description': '逐只股票全量同步每日指标历史数据，8并发，支持Redis中断续继，避免单次6000条上限',
        'category': '行情数据',
        'display_order': 231,
        'points_consumption': 2000,
        'default_params': {'start_date': None}
    },
    'tasks.sync_hsgt_top10': {
        'task': 'tasks.sync_hsgt_top10',
        'name': '沪深股通十大成交股',
        'description': '获取沪股通、深股通每日前十大成交详细数据，每天18~20点之间完成当日更新',
        'category': '行情数据',
        'display_order': 250,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None, 'market_type': None}
    },
    'tasks.sync_hsgt_top10_full_history': {
        'task': 'tasks.sync_hsgt_top10_full_history',
        'name': '沪深股通十大成交股（全量历史）',
        'description': '按月切片全量同步沪深股通十大成交股历史数据（2015年至今），5并发，支持中断续继',
        'category': '行情数据',
        'display_order': 251,
        'default_params': {}
    },
    'tasks.sync_ggt_top10': {
        'task': 'tasks.sync_ggt_top10',
        'name': '港股通十大成交股',
        'description': '获取港股通每日成交数据，包括港股通(沪)、港股通(深)前十大成交详细数据，每天18~20点之间完成当日更新',
        'category': '行情数据',
        'display_order': 260,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None, 'market_type': None}
    },
    'tasks.sync_ggt_top10_full_history': {
        'task': 'tasks.sync_ggt_top10_full_history',
        'name': '港股通十大成交股（全量历史）',
        'description': '逐交易日全量同步港股通十大成交股历史数据（2015年至今），10并发，支持中断续继',
        'category': '行情数据',
        'display_order': 261,
        'default_params': {}
    },
    'tasks.sync_ggt_daily': {
        'task': 'tasks.sync_ggt_daily',
        'name': '港股通每日成交统计',
        'description': '获取港股通每日成交信息，数据从2014年开始（Tushare ggt_daily接口，2000积分/次）',
        'category': '行情数据',
        'display_order': 270,
        'points_consumption': 2000,
        'default_params': {'trade_date': None, 'start_date': None, 'end_date': None}
    },
    'tasks.sync_ggt_daily_full_history': {
        'task': 'tasks.sync_ggt_daily_full_history',
        'name': '港股通每日成交统计（全量历史）',
        'description': '按年切片全量同步港股通每日成交统计历史数据（2014年至今），3并发，支持中断续继',
        'category': '行情数据',
        'display_order': 271,
        'points_consumption': 2000,
        'default_params': {}
    },
    'tasks.sync_ggt_monthly': {
        'task': 'tasks.sync_ggt_monthly',
        'name': '港股通每月成交统计',
        'description': '获取港股通每月成交信息，数据从2014年开始，单次最大1000条（Tushare ggt_monthly接口，5000积分/次）',
        'category': '行情数据',
        'display_order': 272,
        'points_consumption': 5000,
        'default_params': {'month': None, 'start_month': None, 'end_month': None}
    },
    'tasks.sync_ggt_monthly_full_history': {
        'task': 'tasks.sync_ggt_monthly_full_history',
        'name': '港股通每月成交统计（全量历史）',
        'description': '全量同步港股通每月成交历史数据，snapshot 策略，数据量极小（约74条），单次请求获取全量',
        'category': '行情数据',
        'display_order': 273,
        'points_consumption': 5000,
        'default_params': {}
    },

    'tasks.sync_adj_factor': {
        'task': 'tasks.sync_adj_factor',
        'name': '复权因子',
        'description': '获取股票复权因子，可提取单只股票全部历史复权因子，也可以提取单日全部股票的复权因子（盘前9:15~20分更新，2000积分起，5000以上可高频调取）',
        'category': '行情数据',
        'display_order': 280,
        'points_consumption': 2000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_adj_factor_full_history': {
        'task': 'tasks.sync_adj_factor_full_history',
        'name': '复权因子（全量历史）',
        'description': '逐只股票全量同步复权因子历史数据，8并发，支持Redis中断续继，避免单次返回上限6000条问题',
        'category': '行情数据',
        'display_order': 281,
        'points_consumption': None,
        'default_params': {'start_date': None}
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
    'tasks.sync_moneyflow_full_history': {
        'task': 'tasks.sync_moneyflow_full_history',
        'name': '个股资金流向全量历史同步',
        'description': '按股票代码逐只同步个股资金流向全量历史数据，支持中断续继（2000积分/只）',
        'category': '资金流向',
        'display_order': 311,
        'points_consumption': 2000
    },
    'tasks.sync_moneyflow_hsgt': {
        'task': 'tasks.sync_moneyflow_hsgt',
        'name': '沪深港通资金流向',
        'description': '同步沪深港通资金流向数据（北向+南向，2000积分/次）',
        'category': '扩展数据',
        'display_order': 320
    },
    'tasks.sync_moneyflow_hsgt_full_history': {
        'task': 'tasks.sync_moneyflow_hsgt_full_history',
        'name': '沪深港通资金流向全量历史同步',
        'description': '全量同步沪深港通资金流向历史数据（按自然月切片，支持续继，2000积分/次）',
        'category': '资金流向',
        'display_order': 321,
        'points_consumption': 2000
    },
    'tasks.sync_moneyflow_mkt_dc': {
        'task': 'tasks.sync_moneyflow_mkt_dc',
        'name': '大盘资金流向（DC）',
        'description': '同步大盘资金流向数据（东方财富DC，120积分/次）',
        'category': '扩展数据',
        'display_order': 330
    },
    'tasks.sync_moneyflow_mkt_dc_full_history': {
        'task': 'tasks.sync_moneyflow_mkt_dc_full_history',
        'name': '大盘资金流向（DC）全量历史同步',
        'description': '全量同步大盘资金流向历史数据（按自然月切片，支持续继，120积分/次）',
        'category': '资金流向',
        'display_order': 331,
        'points_consumption': 120
    },
    'tasks.sync_moneyflow_ind_dc': {
        'task': 'tasks.sync_moneyflow_ind_dc',
        'name': '板块资金流向（DC）',
        'description': '同步板块资金流向数据（东方财富DC，6000积分/次）',
        'category': '扩展数据',
        'display_order': 340
    },
    'tasks.sync_moneyflow_ind_dc_full_history': {
        'task': 'tasks.sync_moneyflow_ind_dc_full_history',
        'name': '板块资金流向（DC）全量历史',
        'description': '按月切片×三板块类型（行业/概念/地域）全量同步板块资金流向历史数据，支持中断续继（6000积分/次×三类型）',
        'category': '资金流向',
        'display_order': 341
    },
    'tasks.sync_moneyflow_stock_dc': {
        'task': 'tasks.sync_moneyflow_stock_dc',
        'name': '个股资金流向（DC）',
        'description': '同步个股资金流向数据（东方财富DC，5000积分/次）',
        'category': '扩展数据',
        'display_order': 350
    },
    'tasks.sync_moneyflow_stock_dc_full_history': {
        'task': 'tasks.sync_moneyflow_stock_dc_full_history',
        'name': '个股资金流向（DC）全量历史',
        'description': '按股票逐只同步个股资金流向（DC）全量历史数据，支持中断续继（5000积分/次，数据起始20230911）',
        'category': '扩展数据',
        'display_order': 351
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
    'tasks.sync_block_trade': {
        'task': 'tasks.sync_block_trade',
        'name': '大宗交易',
        'description': '同步大宗交易数据（成交价、成交量、成交金额、买卖方营业部等，300积分/次，单次最大1000行）',
        'category': '扩展数据',
        'display_order': 371,
        'points_consumption': 300,
        'default_params': {'trade_date': None, 'ts_code': None, 'start_date': None, 'end_date': None}
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

    'tasks.sync_cyq_perf': {
        'task': 'tasks.sync_cyq_perf',
        'name': '每日筹码及胜率',
        'description': '获取A股每日筹码平均成本和胜率情况，数据从2018年开始，每天18-19点更新（5000积分/天20000次，10000积分/天200000次，15000积分/天不限，单次最大5000条）',
        'category': '特色数据',
        'display_order': 401,
        'points_consumption': 5000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_cyq_chips': {
        'task': 'tasks.sync_cyq_chips',
        'name': '每日筹码分布',
        'description': '获取A股每日的筹码分布情况，提供各价位占比，数据从2018年开始，每天18-19点更新（5000积分/天20000次，10000积分/天200000次，15000积分/天不限，单次最大2000条）',
        'category': '特色数据',
        'display_order': 402,
        'points_consumption': 5000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_ccass_hold': {
        'task': 'tasks.sync_ccass_hold',
        'name': '中央结算系统持股汇总',
        'description': '获取中央结算系统持股汇总数据，覆盖全部历史数据，根据交易所披露时间，当日数据在下一交易日早上9点前完成入库（120积分试用，5000积分正式，每分钟可请求300-500次，单次最大5000条）',
        'category': '特色数据',
        'display_order': 403,
        'points_consumption': 5000,
        'default_params': {'ts_code': None, 'hk_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_ccass_hold_detail': {
        'task': 'tasks.sync_ccass_hold_detail',
        'name': '中央结算系统持股明细',
        'description': '获取中央结算系统机构席位持股明细数据，数据覆盖全历史，根据交易所披露时间，当日数据在下一交易日早上9点前完成（8000积分/次，单次最大6000条，每分钟可请求300次）',
        'category': '特色数据',
        'display_order': 404,
        'points_consumption': 8000,
        'default_params': {'ts_code': None, 'hk_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_hk_hold': {
        'task': 'tasks.sync_hk_hold',
        'name': '沪深港股通持股明细',
        'description': '获取沪深港股通持股明细数据，包含沪股通、深股通、港股通的每日持股情况（120积分试用，2000积分正式）。注意：交易所于2024年8月20开始停止发布日度北向资金数据，改为季度披露',
        'category': '特色数据',
        'display_order': 405,
        'points_consumption': 2000,
        'default_params': {'code': None, 'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None, 'exchange': None}
    },

    'tasks.sync_stk_auction_o': {
        'task': 'tasks.sync_stk_auction_o',
        'name': '股票开盘集合竞价',
        'description': '获取股票开盘9:30集合竞价数据，包含开盘价、收盘价、最高价、最低价、成交量、成交额、均价等数据（需要开通股票分钟权限）。每天盘后更新，单次请求最大返回10000行数据',
        'category': '特色数据',
        'display_order': 406,
        'points_consumption': None,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_stk_auction_c': {
        'task': 'tasks.sync_stk_auction_c',
        'name': '股票收盘集合竞价',
        'description': '股票收盘15:00集合竞价数据，每天盘后更新',
        'category': '特色数据',
        'display_order': 407,
        'points_consumption': None
    },

    'tasks.sync_stk_nineturn': {
        'task': 'tasks.sync_stk_nineturn',
        'name': '神奇九转指标',
        'description': '神奇九转(又称"九转序列")是一种基于技术分析的股票趋势反转指标，通过识别股价在上涨或下跌过程中连续9天的特定走势来判断潜在反转点。数据从2023年开始，每天21点更新，涉及分钟数据（6000积分/次，单次最大10000行）',
        'category': '特色数据',
        'display_order': 408,
        'points_consumption': 6000,
        'default_params': {'ts_code': None, 'trade_date': None, 'freq': 'daily', 'start_date': None, 'end_date': None}
    },

    'tasks.sync_stk_ah_comparison': {
        'task': 'tasks.sync_stk_ah_comparison',
        'name': 'AH股比价',
        'description': 'AH股比价数据，可根据交易日期获取历史数据。用于分析同时在A股和港股上市的股票价格比价。每天盘后17:00更新，数据从2025年8月12日开始，由于历史不好补充，只能累积（5000积分起，单次最大1000行）',
        'category': '特色数据',
        'display_order': 409,
        'points_consumption': 5000,
        'default_params': {'hk_code': None, 'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_stk_surv': {
        'task': 'tasks.sync_stk_surv',
        'name': '机构调研表',
        'description': '获取上市公司机构调研记录数据，包括调研日期、机构参与人员、接待地点、接待方式、接待公司等信息。数据从较早期开始，实时更新（5000积分/次，单次最大100行，可循环或分页提取）',
        'category': '特色数据',
        'display_order': 410,
        'points_consumption': 5000,
        'default_params': {'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_broker_recommend': {
        'task': 'tasks.sync_broker_recommend',
        'name': '券商每月荐股',
        'description': '获取券商月度金股推荐数据，一般在每月1-3日内更新当月数据（6000积分/次，单次最大1000行）',
        'category': '特色数据',
        'display_order': 411,
        'points_consumption': 6000,
        'default_params': {'month': None}
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

    'tasks.sync_forecast': {
        'task': 'tasks.sync_forecast',
        'name': '业绩预告',
        'description': '获取业绩预告数据，包括公告日期、报告期、预告类型、净利润变动幅度、净利润预告值、业绩变动原因等（2000积分/次）',
        'category': '财务数据',
        'display_order': 478,
        'points_consumption': 2000,
        'default_params': {'ts_code': None, 'ann_date': None, 'start_date': None, 'end_date': None, 'period': None, 'type_': None}
    },
    'tasks.sync_forecast_full_history': {
        'task': 'tasks.sync_forecast_full_history',
        'name': '业绩预告全量同步',
        'description': '按季度 period 切片全量同步业绩预告历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 479,
        'points_consumption': 2000
    },

    'tasks.sync_express': {
        'task': 'tasks.sync_express',
        'name': '业绩快报',
        'description': '获取上市公司业绩快报，包括营业收入、利润、资产、每股收益、净资产收益率、同比增长率等（2000积分/次）',
        'category': '财务数据',
        'display_order': 479,
        'points_consumption': 2000,
        'default_params': {'ann_date': None, 'start_date': None, 'end_date': None, 'period': None, 'type_': None}
    },
    'tasks.sync_express_full_history': {
        'task': 'tasks.sync_express_full_history',
        'name': '业绩快报全量同步',
        'description': '按季度 period 切片全量同步业绩快报历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 480,
        'points_consumption': 2000
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

    'tasks.sync_stk_holdernumber': {
        'task': 'tasks.sync_stk_holdernumber',
        'name': '股东人数',
        'description': '获取上市公司股东户数数据（数据不定期公布，包含股票代码、公告日期、截止日期、股东户数等）（600积分/次，单次最大3000行）',
        'category': '参考数据',
        'display_order': 456,
        'points_consumption': 600,
        'default_params': {'ts_code': None, 'ann_date': None, 'start_date': None, 'end_date': None}
    },

    'tasks.sync_stk_holdertrade': {
        'task': 'tasks.sync_stk_holdertrade',
        'name': '股东增减持',
        'description': '获取上市公司股东增减持数据，了解重要股东近期及历史上的股份增减变化（2000积分/次，单次最大3000行）',
        'category': '参考数据',
        'display_order': 457,
        'points_consumption': 2000,
        'default_params': {'ts_code': None, 'ann_date': None, 'start_date': None, 'end_date': None, 'trade_type': None, 'holder_type': None}
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
    # 财务数据同步任务（display_order: 800-899）
    # ============================================
    'tasks.sync_income': {
        'task': 'tasks.sync_income',
        'name': '利润表数据',
        'description': '同步上市公司利润表数据（营业收入、净利润、每股收益等，2000积分/次）',
        'category': '财务数据',
        'display_order': 800,
        'points_consumption': 2000
    },
    'tasks.sync_income_full_history': {
        'task': 'tasks.sync_income_full_history',
        'name': '利润表全量历史同步',
        'description': '按月切片全量同步利润表历史数据，支持中断续继（Redis进度记录）',
        'category': '财务数据',
        'display_order': 801,
        'points_consumption': 2000
    },
    'tasks.sync_balancesheet': {
        'task': 'tasks.sync_balancesheet',
        'name': '资产负债表数据',
        'description': '同步上市公司资产负债表数据（资产、负债、所有者权益等，2000积分/次）',
        'category': '财务数据',
        'display_order': 801,
        'points_consumption': 2000
    },
    'tasks.sync_balancesheet_full_history': {
        'task': 'tasks.sync_balancesheet_full_history',
        'name': '资产负债表全量同步',
        'description': '按季度 period 切片全量同步资产负债表历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 802,
        'points_consumption': 2000
    },
    'tasks.sync_cashflow': {
        'task': 'tasks.sync_cashflow',
        'name': '现金流量表数据',
        'description': '同步上市公司现金流量表数据（经营、投资、筹资活动现金流，2000积分/次）',
        'category': '财务数据',
        'display_order': 803,
        'points_consumption': 2000
    },
    'tasks.sync_cashflow_full_history': {
        'task': 'tasks.sync_cashflow_full_history',
        'name': '现金流量表全量同步',
        'description': '按季度 period 切片全量同步现金流量表历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 804,
        'points_consumption': 2000
    },
    'tasks.sync_dividend': {
        'task': 'tasks.sync_dividend',
        'name': '分红送股数据',
        'description': '同步上市公司分红送股数据（送股、转增、现金分红等，2000积分/次）',
        'category': '财务数据',
        'display_order': 803,
        'points_consumption': 2000
    },
    'tasks.sync_dividend_full_history': {
        'task': 'tasks.sync_dividend_full_history',
        'name': '分红送股全量同步',
        'description': '按季度 end_date 切片全量同步分红送股历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 803,
        'points_consumption': 2000
    },
    'tasks.sync_fina_indicator': {
        'task': 'tasks.sync_fina_indicator',
        'name': '财务指标数据',
        'description': '同步上市公司财务指标数据（150+财务指标，包括EPS、ROE、资产负债率等，2000积分/次，每次最多100条记录）',
        'category': '财务数据',
        'display_order': 805,
        'points_consumption': 2000
    },
    'tasks.sync_fina_indicator_full_history': {
        'task': 'tasks.sync_fina_indicator_full_history',
        'name': '财务指标全量同步',
        'description': '按季度 period 切片全量同步财务指标历史数据，支持中断续继（2000积分/季度）',
        'category': '财务数据',
        'display_order': 8051,
        'points_consumption': 2000
    },
    'tasks.sync_fina_audit': {
        'task': 'tasks.sync_fina_audit',
        'name': '财务审计意见',
        'description': '同步上市公司定期财务审计意见数据（审计结果、审计费用、会计事务所等，500积分/次）',
        'category': '财务数据',
        'display_order': 806,
        'points_consumption': 500
    },
    'tasks.sync_fina_mainbz': {
        'task': 'tasks.sync_fina_mainbz',
        'name': '主营业务构成',
        'description': '同步上市公司主营业务构成数据（按产品/地区/行业分类，2000积分/次）',
        'category': '财务数据',
        'display_order': 807,
        'points_consumption': 2000
    },
    'tasks.sync_fina_mainbz_full_history': {
        'task': 'tasks.sync_fina_mainbz_full_history',
        'name': '主营业务构成（全量历史）',
        'description': '按季度period切片全量同步历史主营业务构成数据，支持Redis续继',
        'category': '财务数据',
        'display_order': 8071,
        'points_consumption': 2000
    },
    'tasks.sync_disclosure_date': {
        'task': 'tasks.sync_disclosure_date',
        'name': '财报披露计划',
        'description': '同步财报披露计划日期（预计披露日期、实际披露日期等，500积分起）',
        'category': '财务数据',
        'display_order': 808,
        'points_consumption': 500
    },
    'tasks.sync_disclosure_date_full_history': {
        'task': 'tasks.sync_disclosure_date_full_history',
        'name': '财报披露计划（全量历史）',
        'description': '按季度period切片全量同步历史财报披露计划数据，支持Redis续继',
        'category': '财务数据',
        'display_order': 8081,
        'points_consumption': 500
    },

    # ============================================
    # 质量监控任务（display_order: 900-999）
    # ============================================
    'quality.daily_report': {
        'task': 'app.tasks.quality_tasks.generate_daily_quality_report',
        'name': '每日质量报告',
        'description': '生成每日数据质量报告',
        'category': '质量监控',
        'display_order': 900
    },
    'quality.weekly_report': {
        'task': 'app.tasks.quality_tasks.generate_weekly_quality_report',
        'name': '周度质量报告',
        'description': '生成周度数据质量趋势报告',
        'category': '质量监控',
        'display_order': 910
    },
    'quality.real_time_check': {
        'task': 'app.tasks.quality_tasks.real_time_quality_check',
        'name': '实时质量检查',
        'description': '实时数据质量检查，发现异常立即告警',
        'category': '质量监控',
        'display_order': 920
    },
    'quality.integrity_check': {
        'task': 'app.tasks.quality_tasks.data_integrity_check',
        'name': '数据完整性检查',
        'description': '检查数据完整性，修复缺失数据',
        'category': '质量监控',
        'display_order': 930
    },
    'quality.trend_analysis': {
        'task': 'app.tasks.quality_tasks.quality_trend_analysis',
        'name': '质量趋势分析',
        'description': '分析数据质量趋势，预测潜在问题',
        'category': '质量监控',
        'display_order': 940
    },
    'quality.cleanup_alerts': {
        'task': 'app.tasks.quality_tasks.cleanup_old_alerts',
        'name': '清理过期告警',
        'description': '清理过期的质量告警记录',
        'category': '质量监控',
        'display_order': 950
    },

    # ============================================
    # 报告通知任务（display_order: 1000-1099）
    # ============================================
    'notification.send_email': {
        'task': 'app.tasks.notification_tasks.send_email_notification',
        'name': '邮件通知',
        'description': '发送邮件通知',
        'category': '报告通知',
        'display_order': 1000
    },
    'notification.send_telegram': {
        'task': 'app.tasks.notification_tasks.send_telegram_notification',
        'name': 'Telegram通知',
        'description': '发送Telegram消息通知',
        'category': '报告通知',
        'display_order': 1010
    },
    'notification.cleanup': {
        'task': 'app.tasks.notification_tasks.cleanup_expired_notifications',
        'name': '清理过期通知',
        'description': '清理过期的通知记录',
        'category': '报告通知',
        'display_order': 1020
    },
    'notification.health_check': {
        'task': 'app.tasks.notification_tasks.notification_health_check',
        'name': '通知系统健康检查',
        'description': '检查通知系统运行状态',
        'category': '报告通知',
        'display_order': 1030
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
    {'name': '财务数据', 'order': 10},
    {'name': '质量监控', 'order': 11},
    {'name': '报告通知', 'order': 12},
    {'name': '系统维护', 'order': 13}
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
