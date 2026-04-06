"""
Tushare 提供者配置常量和元数据

包含积分要求、API限制、市场映射等配置信息
"""

from typing import Dict


class TushareConfig:
    """Tushare Pro API 配置常量"""

    # ========== 积分要求 ==========
    POINTS_DAILY_DATA = 120
    POINTS_MINUTE_DATA = 2000
    POINTS_REALTIME_QUOTES = 5000
    POINTS_NEW_SHARE = 120
    POINTS_STOCK_BASIC = 0  # 免费接口

    # ========== 默认参数 ==========
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1
    DEFAULT_REQUEST_DELAY = 0.2  # 请求间隔（秒）
    DEFAULT_MAX_REQUESTS_PER_MINUTE = 0  # 每分钟最大请求数，0 表示不限速

    # ========== 数据范围 ==========
    DEFAULT_HISTORY_DAYS = 365  # 默认获取一年数据
    DEFAULT_NEW_STOCK_DAYS = 30  # 默认获取30天内新股

    # ========== 分钟周期映射 ==========
    MINUTE_FREQ_MAP: Dict[str, str] = {
        '1': '1min',
        '5': '5min',
        '15': '15min',
        '30': '30min',
        '60': '60min'
    }

    # ========== 市场类型映射 ==========
    MARKET_TYPE_MAP: Dict[str, str] = {
        '主板': '上海主板',
        '创业板': '创业板',
        '科创板': '科创板',
        '北交所': '北交所'
    }

    # ========== 交易所后缀映射 ==========
    @staticmethod
    def get_exchange_suffix(code: str) -> str:
        """
        根据股票代码获取交易所后缀

        Args:
            code: 股票代码（如 '000001'）

        Returns:
            str: 交易所后缀（'SH' 或 'SZ'）
        """
        if code.startswith(('6', '68', '688')):
            return 'SH'  # 上海
        elif code.startswith(('8', '4')):
            return 'BJ'  # 北交所
        elif code.startswith(('0', '2', '3')):
            return 'SZ'  # 深圳
        else:
            return 'SH'  # 默认上海

    @staticmethod
    def parse_market_from_code(code: str) -> str:
        """
        根据股票代码解析市场类型

        Args:
            code: 股票代码

        Returns:
            str: 市场类型
        """
        if not isinstance(code, str):
            return '其他'

        if code.startswith('60') or code.startswith('68'):
            return '上海主板'
        elif code.startswith(('000', '001', '002')):
            return '深圳主板'
        elif code.startswith('300'):
            return '创业板'
        elif code.startswith('688'):
            return '科创板'
        elif code.startswith(('8', '4')):
            return '北交所'
        else:
            return '其他'


class TushareErrorMessages:
    """Tushare API 错误消息常量"""

    # 权限相关错误
    INSUFFICIENT_POINTS = '积分不足'
    INSUFFICIENT_PERMISSION = '权限不足'
    DAILY_LIMIT = '每天最多访问'  # 每日访问次数限制

    # 频率限制错误（明确的限速消息，需等待限速窗口后重试）
    RATE_LIMIT_PER_MINUTE = '抱歉，您每分钟最多访问'
    RATE_LIMIT_PER_HOUR = '抱歉，您每小时最多访问'

    # 通用查询失败（参数错误、offset 超限等，不是限速，不应等待 65s）
    QUERY_FAILED_GENERIC = '查询数据失败，请确认参数'

    @classmethod
    def is_permission_error(cls, error_msg: str) -> bool:
        """判断是否为权限错误"""
        return (cls.INSUFFICIENT_POINTS in error_msg or
                cls.INSUFFICIENT_PERMISSION in error_msg or
                cls.DAILY_LIMIT in error_msg)

    @classmethod
    def is_rate_limit_error(cls, error_msg: str) -> bool:
        """判断是否为频率限制错误（仅明确的限速消息，不含通用查询失败）"""
        return (cls.RATE_LIMIT_PER_MINUTE in error_msg or
                cls.RATE_LIMIT_PER_HOUR in error_msg)


class TushareFields:
    """Tushare API 字段映射"""

    # ========== 股票列表字段 ==========
    # 请求所有可用字段（与 Tushare stock_basic 接口一致）
    STOCK_LIST_FIELDS = (
        'ts_code,symbol,name,area,industry,fullname,enname,cnspell,'
        'market,exchange,curr_type,list_status,list_date,delist_date,'
        'is_hs,act_name,act_ent_type'
    )

    # 字段映射：Tushare 原始字段 → 数据库字段
    STOCK_LIST_RENAME = {
        'ts_code': 'ts_code',        # Tushare 标准代码（如 000001.SZ）
        'symbol': 'code',             # 股票代码（如 000001）
        'name': 'name',               # 股票名称
        'area': 'area',               # 地域
        'industry': 'industry',       # 所属行业
        'fullname': 'fullname',       # 股票全称
        'enname': 'enname',           # 英文全称
        'cnspell': 'cnspell',         # 拼音缩写
        'market': 'market',           # 市场类型（主板/创业板/科创板/CDR）
        'exchange': 'exchange',       # 交易所代码（SSE/SZSE/BSE）
        'curr_type': 'curr_type',     # 交易货币
        'list_status': 'list_status', # 上市状态（L/D/P/G）
        'list_date': 'list_date',     # 上市日期
        'delist_date': 'delist_date', # 退市日期
        'is_hs': 'is_hs',             # 是否沪深港通标的（N/H/S）
        'act_name': 'act_name',       # 实控人名称
        'act_ent_type': 'act_ent_type' # 实控人企业性质
    }

    # 输出字段列表（包含所有 Tushare 字段）
    STOCK_LIST_OUTPUT = [
        'ts_code', 'code', 'name', 'fullname', 'enname', 'cnspell',
        'market', 'exchange', 'area', 'industry', 'curr_type',
        'list_status', 'list_date', 'delist_date', 'is_hs',
        'act_name', 'act_ent_type', 'status'
    ]

    # ========== 日线数据字段 ==========
    DAILY_DATA_RENAME = {
        'trade_date': 'trade_date',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'vol': 'volume',
        'amount': 'amount',
        'pct_chg': 'pct_change'
    }
    DAILY_DATA_OUTPUT = [
        'ts_code', 'trade_date', 'open', 'high', 'low', 'close',
        'volume', 'amount', 'amplitude', 'pct_change',
        'change_amount', 'turnover'
    ]

    # ========== 分钟数据字段 ==========
    MINUTE_DATA_RENAME = {
        'trade_time': 'trade_time',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'close': 'close',
        'vol': 'volume',
        'amount': 'amount'
    }
    MINUTE_DATA_OUTPUT = [
        'trade_time', 'period', 'open', 'high', 'low', 'close',
        'volume', 'amount'
    ]

    # ========== 实时行情字段 ==========
    REALTIME_QUOTE_RENAME = {
        'ts_code': 'ts_code_raw',
        'name': 'name',
        'price': 'latest_price',
        'open': 'open',
        'high': 'high',
        'low': 'low',
        'pre_close': 'pre_close',
        'volume': 'volume',
        'amount': 'amount',
        'pct_chg': 'pct_change',
        'change': 'change_amount'
    }
    REALTIME_QUOTE_OUTPUT = [
        'code', 'name', 'latest_price', 'open', 'high', 'low',
        'pre_close', 'volume', 'amount', 'pct_change',
        'change_amount', 'turnover', 'amplitude', 'trade_time'
    ]

    # ========== 退市股票字段 ==========
    DELISTED_STOCK_FIELDS = 'ts_code,symbol,name,area,industry,market,list_date,delist_date'
    DELISTED_STOCK_OUTPUT = ['code', 'name', 'list_date', 'delist_date', 'market']
