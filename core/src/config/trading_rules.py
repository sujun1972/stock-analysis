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
    """
    交易成本计算规则

    包含印花税、佣金、过户费等所有交易成本的详细配置
    """

    # ========== 印花税 ==========
    # 仅卖出时收取，买入不收
    STAMP_TAX_RATE = 0.001  # 0.1% (国家规定，2023年8月28日起调整为0.1%)

    # ========== 佣金费率 ==========
    # 买入和卖出都收取，不同券商费率可能不同

    # 标准佣金费率配置
    class CommissionRates:
        """券商佣金费率"""
        LOW_RATE = 0.00018       # 万1.8（低佣金账户）
        STANDARD_RATE = 0.00025  # 万2.5（标准账户）
        HIGH_RATE = 0.0003       # 万3（高佣金账户）

        # 默认使用标准费率
        DEFAULT = STANDARD_RATE

    # 最低佣金限制（单笔交易）
    MIN_COMMISSION = 5.0  # 5元（不同券商可能不同，部分互联网券商无最低限制）

    # ========== 过户费 ==========
    # 上海交易所股票，买入和卖出都收取
    # 深圳交易所不收过户费
    TRANSFER_FEE_RATE = 0.00002  # 0.002%（万0.2）

    # ========== 其他费用 ==========
    # 这些费用通常较小，一般可以忽略
    REGULATORY_FEE_RATE = 0.000002  # 证管费（万0.02）
    EXCHANGE_FEE_RATE = 0.00000687  # 经手费（万0.0687）

    # ========== 市场特定配置 ==========
    class MarketSpecificCosts:
        """不同市场的特定成本配置"""

        # 上海交易所（主板、科创板）
        SH_COMMISSION_RATE = 0.00025  # 使用标准佣金率（避免循环引用外部类）
        SH_HAS_TRANSFER_FEE = True  # 有过户费

        # 深圳交易所（主板、中小板、创业板）
        SZ_COMMISSION_RATE = 0.00025  # 使用标准佣金率
        SZ_HAS_TRANSFER_FEE = False  # 无过户费

        # 北交所
        BSE_COMMISSION_RATE = 0.00025  # 使用标准佣金率
        BSE_HAS_TRANSFER_FEE = True  # 有过户费
        BSE_STAMP_TAX_RATE = 0.0005  # 北交所印花税为0.05%（双向收取）

    @staticmethod
    def calculate_buy_cost(
        amount: float,
        stock_code: str = None,
        commission_rate: float = None,
        min_commission: float = None
    ) -> Dict[str, float]:
        """
        计算买入成本

        参数:
            amount: 买入金额
            stock_code: 股票代码（用于判断交易所）
            commission_rate: 自定义佣金费率（None则使用默认值）
            min_commission: 自定义最低佣金（None则使用默认值）

        返回:
            成本明细字典
        """
        # 使用自定义费率或默认费率
        commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT
        min_commission = min_commission if min_commission is not None else TradingCosts.MIN_COMMISSION

        # 计算佣金
        commission = max(amount * commission_rate, min_commission)

        # 判断是否为上海交易所股票（需要过户费）
        is_sh = False
        if stock_code:
            is_sh = MarketType.is_sh_stock(stock_code)

        # 计算过户费
        transfer_fee = amount * TradingCosts.TRANSFER_FEE_RATE if is_sh else 0

        # 计算其他费用（通常可忽略）
        regulatory_fee = amount * TradingCosts.REGULATORY_FEE_RATE
        exchange_fee = amount * TradingCosts.EXCHANGE_FEE_RATE

        total_cost = commission + transfer_fee + regulatory_fee + exchange_fee

        return {
            'commission': commission,
            'transfer_fee': transfer_fee,
            'regulatory_fee': regulatory_fee,
            'exchange_fee': exchange_fee,
            'stamp_tax': 0,  # 买入不收印花税
            'total_cost': total_cost
        }

    @staticmethod
    def calculate_sell_cost(
        amount: float,
        stock_code: str = None,
        commission_rate: float = None,
        min_commission: float = None,
        stamp_tax_rate: float = None
    ) -> Dict[str, float]:
        """
        计算卖出成本

        参数:
            amount: 卖出金额
            stock_code: 股票代码（用于判断交易所）
            commission_rate: 自定义佣金费率（None则使用默认值）
            min_commission: 自定义最低佣金（None则使用默认值）
            stamp_tax_rate: 自定义印花税率（None则使用默认值）

        返回:
            成本明细字典
        """
        # 使用自定义费率或默认费率
        commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT
        min_commission = min_commission if min_commission is not None else TradingCosts.MIN_COMMISSION
        stamp_tax_rate = stamp_tax_rate or TradingCosts.STAMP_TAX_RATE

        # 计算佣金
        commission = max(amount * commission_rate, min_commission)

        # 判断是否为上海交易所股票（需要过户费）
        is_sh = False
        if stock_code:
            is_sh = MarketType.is_sh_stock(stock_code)

        # 计算过户费
        transfer_fee = amount * TradingCosts.TRANSFER_FEE_RATE if is_sh else 0

        # 计算印花税（仅卖出时收取）
        stamp_tax = amount * stamp_tax_rate

        # 计算其他费用（通常可忽略）
        regulatory_fee = amount * TradingCosts.REGULATORY_FEE_RATE
        exchange_fee = amount * TradingCosts.EXCHANGE_FEE_RATE

        total_cost = commission + transfer_fee + stamp_tax + regulatory_fee + exchange_fee

        return {
            'commission': commission,
            'transfer_fee': transfer_fee,
            'stamp_tax': stamp_tax,
            'regulatory_fee': regulatory_fee,
            'exchange_fee': exchange_fee,
            'total_cost': total_cost
        }

    @staticmethod
    def get_total_cost_rate(
        is_buy: bool = True,
        stock_code: str = None,
        commission_rate: float = None
    ) -> float:
        """
        获取总成本费率（简化计算，忽略最低佣金限制）

        参数:
            is_buy: 是否为买入操作
            stock_code: 股票代码
            commission_rate: 佣金费率

        返回:
            总成本费率
        """
        commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT

        # 判断是否为上海交易所股票
        is_sh = False
        if stock_code:
            is_sh = MarketType.is_sh_stock(stock_code)

        # 基础成本 = 佣金
        total_rate = commission_rate

        # 过户费
        if is_sh:
            total_rate += TradingCosts.TRANSFER_FEE_RATE

        # 印花税（仅卖出）
        if not is_buy:
            total_rate += TradingCosts.STAMP_TAX_RATE

        # 其他费用（通常很小）
        total_rate += TradingCosts.REGULATORY_FEE_RATE + TradingCosts.EXCHANGE_FEE_RATE

        return total_rate


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
