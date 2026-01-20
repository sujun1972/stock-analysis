"""
A股交易规则配置文件
包含所有A股市场特定的交易规则和约束
"""

from datetime import time
from typing import Dict, List

# ==================== 交易时间规则 ====================

class TradingHours:
    """交易时间配置"""
    # 集合竞价时间
    MORNING_AUCTION_START = time(9, 15)  # 早盘集合竞价开始
    MORNING_AUCTION_END = time(9, 25)    # 早盘集合竞价结束

    # 连续竞价时间
    MORNING_TRADING_START = time(9, 30)  # 早盘交易开始
    MORNING_TRADING_END = time(11, 30)   # 早盘交易结束

    AFTERNOON_TRADING_START = time(13, 0) # 午盘交易开始
    AFTERNOON_TRADING_END = time(15, 0)   # 午盘交易结束

    # 尾盘集合竞价（科创板/创业板）
    CLOSING_AUCTION_START = time(14, 57)  # 尾盘集合竞价开始
    CLOSING_AUCTION_END = time(15, 0)     # 尾盘集合竞价结束


# ==================== T+1交易制度 ====================

T_PLUS_N = 1  # A股实行T+1交易制度，当日买入次日才能卖出


# ==================== 涨跌幅限制 ====================

class PriceLimitRules:
    """涨跌幅限制规则"""

    # 主板、中小板、创业板（注册制前）
    MAIN_BOARD_LIMIT = 0.10  # ±10%

    # 科创板、创业板（注册制后）、北交所
    STAR_MARKET_LIMIT = 0.20  # ±20%

    # 首日上市特殊规则
    IPO_FIRST_DAY_LIMIT = {
        'main_board': 0.44,      # 主板首日±44%
        'star_market': None,     # 科创板首日无涨跌幅限制
        'gem_market': None,      # 创业板注册制首日无涨跌幅限制
    }

    # ST股票涨跌幅限制
    ST_LIMIT = 0.05  # ST股票±5%

    @staticmethod
    def get_limit(market_type: str, is_st: bool = False, is_first_day: bool = False) -> float:
        """
        获取涨跌幅限制

        参数:
            market_type: 市场类型 ('main', 'star', 'gem', 'bse')
            is_st: 是否为ST股票
            is_first_day: 是否为上市首日

        返回:
            涨跌幅限制比例
        """
        if is_first_day:
            return PriceLimitRules.IPO_FIRST_DAY_LIMIT.get(market_type, 0.10)

        if is_st:
            return PriceLimitRules.ST_LIMIT

        if market_type in ['star', 'gem', 'bse']:
            return PriceLimitRules.STAR_MARKET_LIMIT

        return PriceLimitRules.MAIN_BOARD_LIMIT


# ==================== 交易成本 ====================

class TradingCosts:
    """交易成本计算规则"""

    # 印花税（仅卖出时收取）
    STAMP_TAX_RATE = 0.001  # 0.1%

    # 佣金（买入和卖出都收取）
    COMMISSION_RATE = 0.00025  # 0.025%（万2.5）
    MIN_COMMISSION = 5.0  # 最低佣金5元

    # 过户费（上海交易所股票，买入和卖出都收取）
    TRANSFER_FEE_RATE = 0.00002  # 0.002%（万0.2）

    @staticmethod
    def calculate_buy_cost(amount: float, is_sh: bool = True) -> Dict[str, float]:
        """
        计算买入成本

        参数:
            amount: 买入金额
            is_sh: 是否为上海交易所股票

        返回:
            成本明细字典
        """
        commission = max(amount * TradingCosts.COMMISSION_RATE, TradingCosts.MIN_COMMISSION)
        transfer_fee = amount * TradingCosts.TRANSFER_FEE_RATE if is_sh else 0

        total_cost = commission + transfer_fee

        return {
            'commission': commission,
            'transfer_fee': transfer_fee,
            'stamp_tax': 0,  # 买入不收印花税
            'total_cost': total_cost
        }

    @staticmethod
    def calculate_sell_cost(amount: float, is_sh: bool = True) -> Dict[str, float]:
        """
        计算卖出成本

        参数:
            amount: 卖出金额
            is_sh: 是否为上海交易所股票

        返回:
            成本明细字典
        """
        commission = max(amount * TradingCosts.COMMISSION_RATE, TradingCosts.MIN_COMMISSION)
        transfer_fee = amount * TradingCosts.TRANSFER_FEE_RATE if is_sh else 0
        stamp_tax = amount * TradingCosts.STAMP_TAX_RATE

        total_cost = commission + transfer_fee + stamp_tax

        return {
            'commission': commission,
            'transfer_fee': transfer_fee,
            'stamp_tax': stamp_tax,
            'total_cost': total_cost
        }


# ==================== 交易单位 ====================

class TradingUnits:
    """交易单位规则"""

    LOT_SIZE = 100  # 1手 = 100股

    # 最小交易单位
    MIN_BUY_LOTS = 1  # 买入最少1手（100股）
    MIN_SELL_SHARES = 1  # 卖出最少1股（可以卖零股）

    @staticmethod
    def round_to_lot(shares: int) -> int:
        """将股数向下取整到手的整数倍"""
        return (shares // TradingUnits.LOT_SIZE) * TradingUnits.LOT_SIZE


# ==================== 股票状态过滤规则 ====================

class StockFilterRules:
    """股票过滤规则"""

    # ST股票标识（需要剔除）
    ST_PREFIXES = ['ST', '*ST', 'S*ST', 'SST', 'S']

    # 退市整理期标识
    DELISTING_PREFIXES = ['退市', '*退']

    # 特殊处理标识
    SPECIAL_PREFIXES = ['PT']  # 特别转让

    # 需要排除的股票名称关键词
    EXCLUDE_KEYWORDS = [
        'ST', '退市', 'PT',
        '暂停', '终止', '问询'
    ]

    @staticmethod
    def is_st_stock(stock_name: str) -> bool:
        """判断是否为ST股票"""
        for prefix in StockFilterRules.ST_PREFIXES:
            if stock_name.startswith(prefix):
                return True
        return False

    @staticmethod
    def is_delisting_stock(stock_name: str) -> bool:
        """判断是否为退市整理期股票"""
        for prefix in StockFilterRules.DELISTING_PREFIXES:
            if stock_name.startswith(prefix):
                return True
        return False

    @staticmethod
    def should_exclude(stock_name: str) -> bool:
        """判断是否应该排除该股票"""
        # 检查ST股票
        if StockFilterRules.is_st_stock(stock_name):
            return True

        # 检查退市股票
        if StockFilterRules.is_delisting_stock(stock_name):
            return True

        # 检查其他特殊股票
        for keyword in StockFilterRules.EXCLUDE_KEYWORDS:
            if keyword in stock_name:
                return True

        return False


# ==================== 市场类型映射 ====================

class MarketType:
    """市场类型定义"""

    MAIN_BOARD = 'main'        # 主板
    SMALL_BOARD = 'small'      # 中小板
    GEM = 'gem'                # 创业板
    STAR = 'star'              # 科创板
    BSE = 'bse'                # 北交所
    OTHER = 'other'            # 其他

    # 股票代码前缀到市场类型的映射
    CODE_TO_MARKET = {
        '600': MAIN_BOARD,  # 上海主板
        '601': MAIN_BOARD,  # 上海主板
        '603': MAIN_BOARD,  # 上海主板
        '605': MAIN_BOARD,  # 上海主板
        '688': STAR,        # 科创板
        '000': MAIN_BOARD,  # 深圳主板
        '001': MAIN_BOARD,  # 深圳主板
        '002': SMALL_BOARD, # 中小板
        '300': GEM,         # 创业板
        '301': GEM,         # 创业板（注册制）
        '8': BSE,           # 北交所
        '4': BSE,           # 北交所
    }

    @staticmethod
    def get_market_type(stock_code: str) -> str:
        """根据股票代码获取市场类型"""
        prefix = stock_code[:3]
        return MarketType.CODE_TO_MARKET.get(prefix, MarketType.OTHER)

    @staticmethod
    def is_sh_stock(stock_code: str) -> bool:
        """判断是否为上海交易所股票"""
        return stock_code.startswith(('6', '688', '689'))


# ==================== 数据质量规则 ====================

class DataQualityRules:
    """数据质量检查规则"""

    # 最小交易天数（剔除新上市股票）
    MIN_TRADING_DAYS = 250  # 至少1年交易数据

    # 价格异常检测
    MIN_PRICE = 0.01  # 最低价格（元）
    MAX_PRICE = 10000  # 最高价格（元）

    # 成交量异常检测
    MIN_VOLUME = 0  # 最小成交量
    MAX_DAILY_CHANGE = 0.5  # 单日最大涨跌幅（50%，用于检测异常）

    # 停牌检测
    CONSECUTIVE_ZERO_VOLUME_DAYS = 5  # 连续5天零成交量视为停牌

    @staticmethod
    def is_price_valid(price: float) -> bool:
        """检查价格是否有效"""
        return DataQualityRules.MIN_PRICE <= price <= DataQualityRules.MAX_PRICE

    @staticmethod
    def is_volume_valid(volume: float) -> bool:
        """检查成交量是否有效"""
        return volume >= DataQualityRules.MIN_VOLUME


# ==================== 复权类型 ====================

class AdjustType:
    """复权类型"""

    NONE = ''      # 不复权
    FORWARD = 'qfq'   # 前复权（推荐用于回测）
    BACKWARD = 'hfq'  # 后复权

    # 默认使用前复权
    DEFAULT = FORWARD


# ==================== 导出配置 ====================

__all__ = [
    'TradingHours',
    'T_PLUS_N',
    'PriceLimitRules',
    'TradingCosts',
    'TradingUnits',
    'StockFilterRules',
    'MarketType',
    'DataQualityRules',
    'AdjustType',
]
