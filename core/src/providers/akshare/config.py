"""
AkShare 提供者配置常量和元数据

包含默认参数、市场映射等配置信息
"""

from typing import Dict


class AkShareConfig:
    """AkShare API 配置常量"""

    # ========== 默认参数 ==========
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1
    DEFAULT_REQUEST_DELAY = 0.3  # 请求间隔（秒），避免 IP 限流

    # ========== 数据范围 ==========
    DEFAULT_HISTORY_DAYS = 365  # 默认获取一年数据
    DEFAULT_NEW_STOCK_DAYS = 30  # 默认获取30天内新股
    DEFAULT_MINUTE_DAYS = 5  # 默认获取5天分时数据

    # ========== 分钟周期映射 ==========
    MINUTE_PERIOD_MAP: Dict[str, str] = {
        '1': '1',
        '5': '5',
        '15': '15',
        '30': '30',
        '60': '60'
    }

    # ========== 复权方式映射 ==========
    ADJUST_MAP: Dict[str, str] = {
        'qfq': 'qfq',  # 前复权
        'hfq': 'hfq',  # 后复权
        '': ''  # 不复权
    }

    # ========== 市场类型映射 ==========
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

        if code.startswith('60'):
            return '上海主板'
        elif code.startswith('68'):
            return '上海主板'
        elif code.startswith('000'):
            return '深圳主板'
        elif code.startswith('001'):
            return '深圳主板'
        elif code.startswith('002'):
            return '深圳主板'
        elif code.startswith('300'):
            return '创业板'
        elif code.startswith('688'):
            return '科创板'
        elif code.startswith(('8', '4')):
            return '北交所'
        else:
            return '其他'


class AkShareFields:
    """AkShare API 字段映射"""

    # ========== 股票列表字段 ==========
    STOCK_LIST_RENAME = {
        'code': 'code',
        'name': 'name'
    }
    STOCK_LIST_OUTPUT = ['code', 'name', 'market', 'status']

    # ========== 日线数据字段 ==========
    DAILY_DATA_RENAME = {
        '日期': 'trade_date',
        '开盘': 'open',
        '最高': 'high',
        '最低': 'low',
        '收盘': 'close',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude',
        '涨跌幅': 'pct_change',
        '涨跌额': 'change_amount',
        '换手率': 'turnover'
    }
    DAILY_DATA_OUTPUT = [
        'trade_date', 'open', 'high', 'low', 'close',
        'volume', 'amount', 'amplitude', 'pct_change',
        'change_amount', 'turnover'
    ]

    # ========== 分时数据字段 ==========
    MINUTE_DATA_RENAME = {
        '时间': 'trade_time',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude',
        '涨跌幅': 'pct_change',
        '涨跌额': 'change_amount',
        '换手率': 'turnover'
    }
    MINUTE_DATA_OUTPUT = [
        'trade_time', 'period', 'open', 'high', 'low', 'close',
        'volume', 'amount', 'amplitude', 'pct_change',
        'change_amount', 'turnover'
    ]

    # ========== 实时行情字段（全量接口）==========
    REALTIME_QUOTE_RENAME = {
        '代码': 'code',
        '名称': 'name',
        '最新价': 'latest_price',
        '开盘': 'open',
        '最高': 'high',
        '最低': 'low',
        '昨收': 'pre_close',
        '成交量': 'volume',
        '成交额': 'amount',
        '涨跌幅': 'pct_change',
        '涨跌额': 'change_amount',
        '换手率': 'turnover',
        '振幅': 'amplitude'
    }
    REALTIME_QUOTE_OUTPUT = [
        'code', 'name', 'latest_price', 'open', 'high', 'low',
        'pre_close', 'volume', 'amount', 'pct_change',
        'change_amount', 'turnover', 'amplitude', 'trade_time'
    ]

    # ========== 新股列表字段 ==========
    NEW_STOCK_RENAME = {
        '代码': 'code',
        '名称': 'name',
        '上市日期': 'list_date'
    }
    NEW_STOCK_OUTPUT = ['code', 'name', 'market', 'list_date', 'status']

    # ========== 退市股票字段 ==========
    DELISTED_STOCK_RENAME_SH = {
        '公司代码': 'code',
        '公司简称': 'name',
        '上市日期': 'list_date',
        '暂停上市日期': 'delist_date'
    }
    DELISTED_STOCK_RENAME_SZ = {
        '公司代码': 'code',
        '公司简称': 'name',
        '上市日期': 'list_date',
        '终止上市日期': 'delist_date'
    }
    DELISTED_STOCK_OUTPUT = ['code', 'name', 'list_date', 'delist_date', 'market']


class AkShareNotes:
    """AkShare 使用注意事项"""

    RATE_LIMIT_WARNING = """
    AkShare 数据来源于公开网站爬虫，存在以下限制：
    1. IP 限流风险：避免过于频繁的请求
    2. 建议请求间隔 >= 0.3秒
    3. 实时行情获取较慢（需要爬取多个页面）
    4. 非交易时段部分接口可能无响应
    """

    REALTIME_QUOTE_WARNING = """
    AkShare 实时行情说明：
    - 全量获取需要分58个批次请求，耗时3-5分钟
    - 批量获取（<500只）使用单个股票接口，速度更快
    - 建议用于定时批量更新，不适合高频调用
    """

    DATA_SOURCE_INFO = """
    AkShare 数据来源：
    - 股票列表：东方财富、新浪财经
    - 日线数据：东方财富
    - 分时数据：东方财富
    - 实时行情：东方财富
    - 新股数据：东方财富
    - 退市数据：上交所、深交所官网
    """
