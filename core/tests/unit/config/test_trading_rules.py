#!/usr/bin/env python3
"""
config/trading_rules.py 模块的完整测试套件

测试覆盖:
1. TradingHours - 交易时间配置
2. T_PLUS_N - T+1交易制度
3. PriceLimitRules - 涨跌幅限制
4. TradingCosts - 交易成本计算
5. TradingUnits - 交易单位
6. StockFilterRules - 股票过滤规则
7. MarketType - 市场类型判断
8. DataQualityRules - 数据质量规则
9. AdjustType - 复权类型
"""

import pytest
from datetime import time


class TestTradingHours:
    """测试交易时间配置"""

    def test_morning_auction_times(self):
        """测试早盘集合竞价时间"""
        from src.config.trading_rules import TradingHours

        assert TradingHours.MORNING_AUCTION_START == time(9, 15)
        assert TradingHours.MORNING_AUCTION_END == time(9, 25)

    def test_morning_trading_times(self):
        """测试早盘交易时间"""
        from src.config.trading_rules import TradingHours

        assert TradingHours.MORNING_TRADING_START == time(9, 30)
        assert TradingHours.MORNING_TRADING_END == time(11, 30)

    def test_afternoon_trading_times(self):
        """测试午盘交易时间"""
        from src.config.trading_rules import TradingHours

        assert TradingHours.AFTERNOON_TRADING_START == time(13, 0)
        assert TradingHours.AFTERNOON_TRADING_END == time(15, 0)

    def test_closing_auction_times(self):
        """测试尾盘集合竞价时间"""
        from src.config.trading_rules import TradingHours

        assert TradingHours.CLOSING_AUCTION_START == time(14, 57)
        assert TradingHours.CLOSING_AUCTION_END == time(15, 0)

    def test_all_times_are_time_objects(self):
        """测试所有时间都是 time 对象"""
        from src.config.trading_rules import TradingHours

        assert isinstance(TradingHours.MORNING_AUCTION_START, time)
        assert isinstance(TradingHours.MORNING_AUCTION_END, time)
        assert isinstance(TradingHours.MORNING_TRADING_START, time)
        assert isinstance(TradingHours.MORNING_TRADING_END, time)
        assert isinstance(TradingHours.AFTERNOON_TRADING_START, time)
        assert isinstance(TradingHours.AFTERNOON_TRADING_END, time)
        assert isinstance(TradingHours.CLOSING_AUCTION_START, time)
        assert isinstance(TradingHours.CLOSING_AUCTION_END, time)


class TestTPlusN:
    """测试T+1交易制度"""

    def test_t_plus_n_value(self):
        """测试T+1值为1"""
        from src.config.trading_rules import T_PLUS_N

        assert T_PLUS_N == 1

    def test_t_plus_n_type(self):
        """测试T+1类型为整数"""
        from src.config.trading_rules import T_PLUS_N

        assert isinstance(T_PLUS_N, int)


class TestPriceLimitRules:
    """测试涨跌幅限制规则"""

    def test_main_board_limit(self):
        """测试主板涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.MAIN_BOARD_LIMIT == 0.10

    def test_star_market_limit(self):
        """测试科创板涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.STAR_MARKET_LIMIT == 0.20

    def test_st_limit(self):
        """测试ST股票涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.ST_LIMIT == 0.05

    def test_ipo_first_day_limit_structure(self):
        """测试首日涨跌幅限制结构"""
        from src.config.trading_rules import PriceLimitRules

        assert 'main_board' in PriceLimitRules.IPO_FIRST_DAY_LIMIT
        assert 'star_market' in PriceLimitRules.IPO_FIRST_DAY_LIMIT
        assert 'gem_market' in PriceLimitRules.IPO_FIRST_DAY_LIMIT

    def test_ipo_first_day_main_board(self):
        """测试主板首日涨跌幅"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.IPO_FIRST_DAY_LIMIT['main_board'] == 0.44

    def test_ipo_first_day_star_market(self):
        """测试科创板首日无涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.IPO_FIRST_DAY_LIMIT['star_market'] is None

    def test_ipo_first_day_gem_market(self):
        """测试创业板首日无涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        assert PriceLimitRules.IPO_FIRST_DAY_LIMIT['gem_market'] is None

    def test_get_limit_main_board(self):
        """测试获取主板涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('main')
        assert limit == 0.10

    def test_get_limit_star_market(self):
        """测试获取科创板涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('star')
        assert limit == 0.20

    def test_get_limit_gem_market(self):
        """测试获取创业板涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('gem')
        assert limit == 0.20

    def test_get_limit_bse_market(self):
        """测试获取北交所涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('bse')
        assert limit == 0.20

    def test_get_limit_st_stock(self):
        """测试获取ST股票涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('main', is_st=True)
        assert limit == 0.05

    def test_get_limit_first_day_main_board(self):
        """测试主板首日涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('main_board', is_first_day=True)
        assert limit == 0.44

    def test_get_limit_first_day_star_market(self):
        """测试科创板首日涨跌幅限制"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('star_market', is_first_day=True)
        assert limit is None

    def test_get_limit_first_day_unknown_market(self):
        """测试未知市场首日默认涨跌幅"""
        from src.config.trading_rules import PriceLimitRules

        limit = PriceLimitRules.get_limit('unknown', is_first_day=True)
        assert limit == 0.10


class TestTradingCosts:
    """测试交易成本计算"""

    def test_stamp_tax_rate(self):
        """测试印花税率"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.STAMP_TAX_RATE == 0.001

    def test_commission_rates(self):
        """测试佣金费率"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.CommissionRates.LOW_RATE == 0.00018
        assert TradingCosts.CommissionRates.STANDARD_RATE == 0.00025
        assert TradingCosts.CommissionRates.HIGH_RATE == 0.0003
        assert TradingCosts.CommissionRates.DEFAULT == 0.00025

    def test_min_commission(self):
        """测试最低佣金"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.MIN_COMMISSION == 5.0

    def test_transfer_fee_rate(self):
        """测试过户费率"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.TRANSFER_FEE_RATE == 0.00002

    def test_regulatory_fee_rate(self):
        """测试证管费率"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.REGULATORY_FEE_RATE == 0.000002

    def test_exchange_fee_rate(self):
        """测试经手费率"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.EXCHANGE_FEE_RATE == 0.00000687

    def test_market_specific_costs_sh(self):
        """测试上海交易所特定成本"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.MarketSpecificCosts.SH_COMMISSION_RATE == 0.00025
        assert TradingCosts.MarketSpecificCosts.SH_HAS_TRANSFER_FEE is True

    def test_market_specific_costs_sz(self):
        """测试深圳交易所特定成本"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.MarketSpecificCosts.SZ_COMMISSION_RATE == 0.00025
        assert TradingCosts.MarketSpecificCosts.SZ_HAS_TRANSFER_FEE is False

    def test_market_specific_costs_bse(self):
        """测试北交所特定成本"""
        from src.config.trading_rules import TradingCosts

        assert TradingCosts.MarketSpecificCosts.BSE_COMMISSION_RATE == 0.00025
        assert TradingCosts.MarketSpecificCosts.BSE_HAS_TRANSFER_FEE is True
        assert TradingCosts.MarketSpecificCosts.BSE_STAMP_TAX_RATE == 0.0005

    def test_calculate_buy_cost_basic(self):
        """测试基本买入成本计算"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_buy_cost(10000)

        assert 'commission' in cost
        assert 'transfer_fee' in cost
        assert 'stamp_tax' in cost
        assert 'regulatory_fee' in cost
        assert 'exchange_fee' in cost
        assert 'total_cost' in cost
        assert cost['stamp_tax'] == 0  # 买入不收印花税

    def test_calculate_buy_cost_with_sh_stock(self):
        """测试上海股票买入成本（有过户费）"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_buy_cost(10000, stock_code='600000')

        assert cost['transfer_fee'] > 0
        assert cost['transfer_fee'] == 10000 * TradingCosts.TRANSFER_FEE_RATE

    def test_calculate_buy_cost_with_sz_stock(self):
        """测试深圳股票买入成本（无过户费）"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_buy_cost(10000, stock_code='000001')

        assert cost['transfer_fee'] == 0

    def test_calculate_buy_cost_min_commission(self):
        """测试最低佣金限制"""
        from src.config.trading_rules import TradingCosts

        # 小额交易，应该按最低佣金计算
        cost = TradingCosts.calculate_buy_cost(100)

        assert cost['commission'] == TradingCosts.MIN_COMMISSION

    def test_calculate_buy_cost_custom_commission(self):
        """测试自定义佣金费率"""
        from src.config.trading_rules import TradingCosts

        custom_rate = 0.0001
        cost = TradingCosts.calculate_buy_cost(100000, commission_rate=custom_rate)

        expected_commission = max(100000 * custom_rate, TradingCosts.MIN_COMMISSION)
        assert cost['commission'] == expected_commission

    def test_calculate_buy_cost_custom_min_commission(self):
        """测试自定义最低佣金"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_buy_cost(100, min_commission=1.0)

        assert cost['commission'] == 1.0

    def test_calculate_sell_cost_basic(self):
        """测试基本卖出成本计算"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_sell_cost(10000)

        assert 'commission' in cost
        assert 'transfer_fee' in cost
        assert 'stamp_tax' in cost
        assert 'regulatory_fee' in cost
        assert 'exchange_fee' in cost
        assert 'total_cost' in cost
        assert cost['stamp_tax'] > 0  # 卖出收印花税

    def test_calculate_sell_cost_stamp_tax(self):
        """测试卖出印花税"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_sell_cost(10000)

        expected_stamp_tax = 10000 * TradingCosts.STAMP_TAX_RATE
        assert cost['stamp_tax'] == expected_stamp_tax

    def test_calculate_sell_cost_with_sh_stock(self):
        """测试上海股票卖出成本（有过户费）"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_sell_cost(10000, stock_code='600000')

        assert cost['transfer_fee'] > 0

    def test_calculate_sell_cost_with_sz_stock(self):
        """测试深圳股票卖出成本（无过户费）"""
        from src.config.trading_rules import TradingCosts

        cost = TradingCosts.calculate_sell_cost(10000, stock_code='000001')

        assert cost['transfer_fee'] == 0

    def test_calculate_sell_cost_custom_stamp_tax(self):
        """测试自定义印花税率"""
        from src.config.trading_rules import TradingCosts

        custom_stamp_tax = 0.002
        cost = TradingCosts.calculate_sell_cost(10000, stamp_tax_rate=custom_stamp_tax)

        assert cost['stamp_tax'] == 10000 * custom_stamp_tax

    def test_get_total_cost_rate_buy(self):
        """测试买入总成本费率"""
        from src.config.trading_rules import TradingCosts

        rate = TradingCosts.get_total_cost_rate(is_buy=True)

        # 买入费率 = 佣金 + 其他费用（不含印花税）
        assert rate > 0
        assert rate < 0.01  # 应该小于1%

    def test_get_total_cost_rate_sell(self):
        """测试卖出总成本费率"""
        from src.config.trading_rules import TradingCosts

        rate = TradingCosts.get_total_cost_rate(is_buy=False)

        # 卖出费率 = 佣金 + 印花税 + 其他费用
        assert rate > 0
        assert rate > TradingCosts.STAMP_TAX_RATE  # 应该大于印花税率

    def test_get_total_cost_rate_sh_stock(self):
        """测试上海股票总成本费率（含过户费）"""
        from src.config.trading_rules import TradingCosts

        rate = TradingCosts.get_total_cost_rate(is_buy=True, stock_code='600000')

        # 应该包含过户费
        rate_without_transfer = TradingCosts.get_total_cost_rate(is_buy=True, stock_code='000001')
        assert rate > rate_without_transfer

    def test_get_total_cost_rate_custom_commission(self):
        """测试自定义佣金费率的总成本"""
        from src.config.trading_rules import TradingCosts

        custom_rate = 0.0001
        rate = TradingCosts.get_total_cost_rate(is_buy=True, commission_rate=custom_rate)

        assert rate >= custom_rate


class TestTradingUnits:
    """测试交易单位规则"""

    def test_lot_size(self):
        """测试手的大小"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.LOT_SIZE == 100

    def test_min_buy_lots(self):
        """测试最小买入手数"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.MIN_BUY_LOTS == 1

    def test_min_sell_shares(self):
        """测试最小卖出股数"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.MIN_SELL_SHARES == 1

    def test_round_to_lot_exact(self):
        """测试整手股数向下取整"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.round_to_lot(100) == 100
        assert TradingUnits.round_to_lot(200) == 200
        assert TradingUnits.round_to_lot(1000) == 1000

    def test_round_to_lot_with_remainder(self):
        """测试有余数的股数向下取整"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.round_to_lot(150) == 100
        assert TradingUnits.round_to_lot(250) == 200
        assert TradingUnits.round_to_lot(199) == 100
        assert TradingUnits.round_to_lot(99) == 0

    def test_round_to_lot_zero(self):
        """测试零股向下取整"""
        from src.config.trading_rules import TradingUnits

        assert TradingUnits.round_to_lot(0) == 0
        assert TradingUnits.round_to_lot(50) == 0


class TestStockFilterRules:
    """测试股票过滤规则"""

    def test_st_prefixes(self):
        """测试ST股票前缀"""
        from src.config.trading_rules import StockFilterRules

        assert 'ST' in StockFilterRules.ST_PREFIXES
        assert '*ST' in StockFilterRules.ST_PREFIXES
        assert 'S*ST' in StockFilterRules.ST_PREFIXES

    def test_delisting_prefixes(self):
        """测试退市股票前缀"""
        from src.config.trading_rules import StockFilterRules

        assert '退市' in StockFilterRules.DELISTING_PREFIXES
        assert '*退' in StockFilterRules.DELISTING_PREFIXES

    def test_special_prefixes(self):
        """测试特殊处理前缀"""
        from src.config.trading_rules import StockFilterRules

        assert 'PT' in StockFilterRules.SPECIAL_PREFIXES

    def test_exclude_keywords(self):
        """测试排除关键词"""
        from src.config.trading_rules import StockFilterRules

        assert 'ST' in StockFilterRules.EXCLUDE_KEYWORDS
        assert '退市' in StockFilterRules.EXCLUDE_KEYWORDS

    def test_is_st_stock_true(self):
        """测试识别ST股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.is_st_stock('ST股票') is True
        assert StockFilterRules.is_st_stock('*ST股票') is True
        assert StockFilterRules.is_st_stock('S*ST股票') is True

    def test_is_st_stock_false(self):
        """测试非ST股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.is_st_stock('正常股票') is False
        assert StockFilterRules.is_st_stock('中国平安') is False

    def test_is_delisting_stock_true(self):
        """测试识别退市股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.is_delisting_stock('退市股票') is True
        assert StockFilterRules.is_delisting_stock('*退股票') is True

    def test_is_delisting_stock_false(self):
        """测试非退市股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.is_delisting_stock('正常股票') is False
        assert StockFilterRules.is_delisting_stock('中国平安') is False

    def test_should_exclude_st(self):
        """测试排除ST股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.should_exclude('ST股票') is True

    def test_should_exclude_delisting(self):
        """测试排除退市股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.should_exclude('退市股票') is True

    def test_should_exclude_keywords(self):
        """测试排除包含关键词的股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.should_exclude('暂停上市') is True
        assert StockFilterRules.should_exclude('终止上市') is True

    def test_should_exclude_normal(self):
        """测试不排除正常股票"""
        from src.config.trading_rules import StockFilterRules

        assert StockFilterRules.should_exclude('中国平安') is False
        assert StockFilterRules.should_exclude('贵州茅台') is False


class TestMarketType:
    """测试市场类型映射"""

    def test_market_constants(self):
        """测试市场类型常量"""
        from src.config.trading_rules import MarketType

        assert MarketType.MAIN_BOARD == 'main'
        assert MarketType.SMALL_BOARD == 'small'
        assert MarketType.GEM == 'gem'
        assert MarketType.STAR == 'star'
        assert MarketType.BSE == 'bse'
        assert MarketType.OTHER == 'other'

    def test_code_to_market_mapping(self):
        """测试代码到市场的映射"""
        from src.config.trading_rules import MarketType

        assert '600' in MarketType.CODE_TO_MARKET
        assert '688' in MarketType.CODE_TO_MARKET
        assert '000' in MarketType.CODE_TO_MARKET
        assert '002' in MarketType.CODE_TO_MARKET
        assert '300' in MarketType.CODE_TO_MARKET

    def test_get_market_type_sh_main(self):
        """测试获取上海主板市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('600000') == 'main'
        assert MarketType.get_market_type('601000') == 'main'
        assert MarketType.get_market_type('603000') == 'main'

    def test_get_market_type_star(self):
        """测试获取科创板市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('688000') == 'star'

    def test_get_market_type_sz_main(self):
        """测试获取深圳主板市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('000001') == 'main'

    def test_get_market_type_small_board(self):
        """测试获取中小板市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('002000') == 'small'

    def test_get_market_type_gem(self):
        """测试获取创业板市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('300000') == 'gem'
        assert MarketType.get_market_type('301000') == 'gem'

    def test_get_market_type_bse(self):
        """测试获取北交所市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('8') == 'bse'
        assert MarketType.get_market_type('4') == 'bse'

    def test_get_market_type_other(self):
        """测试获取未知市场类型"""
        from src.config.trading_rules import MarketType

        assert MarketType.get_market_type('999999') == 'other'

    def test_is_sh_stock_true(self):
        """测试识别上海股票"""
        from src.config.trading_rules import MarketType

        assert MarketType.is_sh_stock('600000') is True
        assert MarketType.is_sh_stock('688000') is True
        assert MarketType.is_sh_stock('689000') is True

    def test_is_sh_stock_false(self):
        """测试识别非上海股票"""
        from src.config.trading_rules import MarketType

        assert MarketType.is_sh_stock('000001') is False
        assert MarketType.is_sh_stock('002000') is False
        assert MarketType.is_sh_stock('300000') is False


class TestDataQualityRules:
    """测试数据质量规则"""

    def test_min_trading_days(self):
        """测试最小交易天数"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.MIN_TRADING_DAYS == 250

    def test_price_limits(self):
        """测试价格限制"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.MIN_PRICE == 0.01
        assert DataQualityRules.MAX_PRICE == 10000

    def test_volume_limits(self):
        """测试成交量限制"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.MIN_VOLUME == 0

    def test_max_daily_change(self):
        """测试最大日涨跌幅"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.MAX_DAILY_CHANGE == 0.5

    def test_consecutive_zero_volume_days(self):
        """测试连续零成交量天数"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.CONSECUTIVE_ZERO_VOLUME_DAYS == 5

    def test_is_price_valid_true(self):
        """测试有效价格"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.is_price_valid(10.0) is True
        assert DataQualityRules.is_price_valid(0.01) is True
        assert DataQualityRules.is_price_valid(100.0) is True
        assert DataQualityRules.is_price_valid(9999.0) is True

    def test_is_price_valid_false(self):
        """测试无效价格"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.is_price_valid(0.0) is False
        assert DataQualityRules.is_price_valid(-1.0) is False
        assert DataQualityRules.is_price_valid(10001.0) is False

    def test_is_price_valid_boundary(self):
        """测试边界价格"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.is_price_valid(0.01) is True
        assert DataQualityRules.is_price_valid(10000) is True

    def test_is_volume_valid_true(self):
        """测试有效成交量"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.is_volume_valid(0) is True
        assert DataQualityRules.is_volume_valid(100) is True
        assert DataQualityRules.is_volume_valid(1000000) is True

    def test_is_volume_valid_false(self):
        """测试无效成交量"""
        from src.config.trading_rules import DataQualityRules

        assert DataQualityRules.is_volume_valid(-1) is False
        assert DataQualityRules.is_volume_valid(-100) is False


class TestAdjustType:
    """测试复权类型"""

    def test_adjust_types(self):
        """测试复权类型常量"""
        from src.config.trading_rules import AdjustType

        assert AdjustType.NONE == ''
        assert AdjustType.FORWARD == 'qfq'
        assert AdjustType.BACKWARD == 'hfq'

    def test_default_adjust_type(self):
        """测试默认复权类型"""
        from src.config.trading_rules import AdjustType

        assert AdjustType.DEFAULT == 'qfq'
        assert AdjustType.DEFAULT == AdjustType.FORWARD


class TestModuleExports:
    """测试模块导出"""

    def test_all_exports(self):
        """测试 __all__ 包含所有导出"""
        from src.config.trading_rules import __all__

        expected_exports = [
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

        for export in expected_exports:
            assert export in __all__, f"Missing export: {export}"

    def test_all_exports_accessible(self):
        """测试所有导出可访问"""
        from src.config.trading_rules import __all__
        import src.config.trading_rules as trading_rules_module

        for name in __all__:
            assert hasattr(trading_rules_module, name), f"Cannot access: {name}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
