"""
回测交易执行器
负责执行买入/卖出/做空/平空订单，计算滑点和交易成本
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from src.config.trading_rules import TradingCosts
from .cost_analyzer import TradingCostAnalyzer
from .slippage_models import SlippageModel, FixedSlippageModel
from .short_selling import ShortSellingCosts, ShortPosition
from .backtest_portfolio import BacktestPortfolio


class BacktestExecutor:
    """回测交易执行器"""

    def __init__(
        self,
        commission_rate: float,
        stamp_tax_rate: float,
        min_commission: float,
        slippage_model: SlippageModel,
        cost_analyzer: TradingCostAnalyzer,
        market_data_cache: Dict = None
    ):
        """
        初始化交易执行器

        参数:
            commission_rate: 佣金费率
            stamp_tax_rate: 印花税率
            min_commission: 最小佣金
            slippage_model: 滑点模型
            cost_analyzer: 成本分析器
            market_data_cache: 市场数据缓存
        """
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.min_commission = min_commission
        self.slippage_model = slippage_model
        self.cost_analyzer = cost_analyzer
        self.market_data_cache = market_data_cache or {}

    def calculate_actual_price_with_slippage(
        self,
        stock_code: str,
        reference_price: float,
        shares: int,
        is_buy: bool,
        date: datetime = None
    ) -> float:
        """
        使用滑点模型计算实际成交价格

        参数:
            stock_code: 股票代码
            reference_price: 参考价格
            shares: 股数
            is_buy: 是否买入
            date: 交易日期

        返回:
            实际成交价格
        """
        order_size = shares * reference_price
        kwargs = {}

        # 准备市场数据（成交量、波动率、盘口）
        if 'volumes' in self.market_data_cache and date is not None:
            volumes_df = self.market_data_cache['volumes']
            if date in volumes_df.index and stock_code in volumes_df.columns:
                recent_volumes = volumes_df.loc[:date, stock_code].tail(20)
                avg_volume = recent_volumes.mean() if len(recent_volumes) > 0 else None
                if avg_volume and not np.isnan(avg_volume):
                    kwargs['avg_volume'] = avg_volume * reference_price

        if 'volatilities' in self.market_data_cache and date is not None:
            vol_df = self.market_data_cache['volatilities']
            if date in vol_df.index and stock_code in vol_df.columns:
                volatility = vol_df.loc[date, stock_code]
                if not np.isnan(volatility):
                    kwargs['volatility'] = volatility

        if 'bid_prices' in self.market_data_cache and date is not None:
            bid_df = self.market_data_cache['bid_prices']
            ask_df = self.market_data_cache.get('ask_prices')

            if (bid_df is not None and date in bid_df.index and stock_code in bid_df.columns and
                ask_df is not None and date in ask_df.index and stock_code in ask_df.columns):

                bid_price = bid_df.loc[date, stock_code]
                ask_price = ask_df.loc[date, stock_code]

                if not np.isnan(bid_price) and not np.isnan(ask_price):
                    kwargs['bid_price'] = bid_price
                    kwargs['ask_price'] = ask_price

        # 使用滑点模型计算
        actual_price = self.slippage_model.get_actual_price(
            order_size=order_size,
            reference_price=reference_price,
            is_buy=is_buy,
            **kwargs
        )

        return actual_price

    def calculate_trading_cost(
        self,
        amount: float,
        is_buy: bool,
        stock_code: str = None
    ) -> float:
        """
        计算交易成本

        参数:
            amount: 交易金额
            is_buy: 是否买入
            stock_code: 股票代码

        返回:
            交易成本
        """
        if is_buy:
            costs = TradingCosts.calculate_buy_cost(
                amount,
                stock_code=stock_code,
                commission_rate=self.commission_rate,
                min_commission=self.min_commission
            )
        else:
            costs = TradingCosts.calculate_sell_cost(
                amount,
                stock_code=stock_code,
                commission_rate=self.commission_rate,
                min_commission=self.min_commission,
                stamp_tax_rate=self.stamp_tax_rate
            )

        return costs['total_cost']

    def execute_buy(
        self,
        portfolio: BacktestPortfolio,
        stock_code: str,
        buy_price: float,
        capital: float,
        date: datetime
    ) -> bool:
        """
        执行买入订单

        参数:
            portfolio: 组合管理器
            stock_code: 股票代码
            buy_price: 买入价格
            capital: 可用资金
            date: 交易日期

        返回:
            是否成功执行
        """
        # 估算股数
        estimated_shares = int(capital / buy_price / 100) * 100

        if estimated_shares < 100:
            return False

        # 计算实际价格
        actual_price = self.calculate_actual_price_with_slippage(
            stock_code=stock_code,
            reference_price=buy_price,
            shares=estimated_shares,
            is_buy=True,
            date=date
        )

        # 重新计算可买股数
        max_shares = int(capital / actual_price / 100) * 100

        if max_shares < 100:
            return False

        # 计算成本
        buy_amount = max_shares * actual_price
        cost = self.calculate_trading_cost(buy_amount, is_buy=True, stock_code=stock_code)

        # 检查资金
        if portfolio.get_cash() < (buy_amount + cost):
            return False

        # 记录交易
        self.cost_analyzer.add_trade_from_dict(
            date=date,
            stock_code=stock_code,
            action='buy',
            shares=max_shares,
            price=actual_price,
            commission=cost,
            stamp_tax=0.0,
            slippage=max_shares * (actual_price - buy_price)
        )

        # 更新组合
        portfolio.update_cash(-(buy_amount + cost))
        portfolio.add_long_position(stock_code, max_shares, actual_price, date)

        return True

    def execute_sell(
        self,
        portfolio: BacktestPortfolio,
        stock_code: str,
        sell_price: float,
        date: datetime
    ) -> bool:
        """
        执行卖出订单

        参数:
            portfolio: 组合管理器
            stock_code: 股票代码
            sell_price: 卖出价格
            date: 交易日期

        返回:
            是否成功执行
        """
        pos = portfolio.get_long_position(stock_code)
        if not pos:
            return False

        # 计算实际价格
        actual_price = self.calculate_actual_price_with_slippage(
            stock_code=stock_code,
            reference_price=sell_price,
            shares=pos['shares'],
            is_buy=False,
            date=date
        )

        # 计算成本
        sell_amount = pos['shares'] * actual_price
        cost = self.calculate_trading_cost(sell_amount, is_buy=False, stock_code=stock_code)

        # ��录交易
        self.cost_analyzer.add_trade_from_dict(
            date=date,
            stock_code=stock_code,
            action='sell',
            shares=pos['shares'],
            price=actual_price,
            commission=cost * 0.5,
            stamp_tax=sell_amount * self.stamp_tax_rate,
            slippage=pos['shares'] * (sell_price - actual_price)
        )

        # 更新组合
        portfolio.update_cash(sell_amount - cost)
        portfolio.remove_long_position(stock_code)

        return True

    def execute_short_sell(
        self,
        portfolio: BacktestPortfolio,
        stock_code: str,
        short_price: float,
        capital: float,
        margin_ratio: float,
        margin_rate: float,
        date: datetime
    ) -> bool:
        """
        执行融券卖出订单

        参数:
            portfolio: 组合管理器
            stock_code: 股票代码
            short_price: 卖出价格
            capital: 可用资金
            margin_ratio: 保证金比例
            margin_rate: 融券年化费率
            date: 交易日期

        返回:
            是否成功执行
        """
        # 估算股数
        estimated_shares = int(capital / short_price / 100) * 100

        if estimated_shares < 100:
            return False

        # 计算实际价格
        actual_price = self.calculate_actual_price_with_slippage(
            stock_code=stock_code,
            reference_price=short_price,
            shares=estimated_shares,
            is_buy=False,
            date=date
        )

        max_shares = int(capital / actual_price / 100) * 100

        if max_shares < 100:
            return False

        short_amount = max_shares * actual_price

        # 融券成本
        short_costs = ShortSellingCosts.calculate_short_sell_cost(
            amount=short_amount,
            stock_code=stock_code,
            commission_rate=self.commission_rate,
            min_commission=self.min_commission
        )

        # 所需保证金
        required_margin = ShortSellingCosts.calculate_required_margin(
            short_amount=short_amount,
            margin_ratio=margin_ratio
        )

        # 检查资金
        if portfolio.get_cash() < (required_margin + short_costs['total_cost']):
            return False

        # 记录交易
        self.cost_analyzer.add_trade_from_dict(
            date=date,
            stock_code=stock_code,
            action='short_sell',
            shares=max_shares,
            price=actual_price,
            commission=short_costs['commission'],
            stamp_tax=0.0,
            slippage=max_shares * (short_price - actual_price)
        )

        # 更新组合
        portfolio.update_cash(short_amount - required_margin - short_costs['total_cost'])
        portfolio.add_short_position(stock_code, max_shares, actual_price, date, margin_rate)

        return True

    def execute_cover_short(
        self,
        portfolio: BacktestPortfolio,
        stock_code: str,
        cover_price: float,
        date: datetime
    ) -> bool:
        """
        执行平空订单（买券还券）

        参数:
            portfolio: 组合管理器
            stock_code: 股票代码
            cover_price: 平仓价格
            date: 交易日期

        返回:
            是否成功执行
        """
        short_pos = portfolio.get_short_position(stock_code)
        if not short_pos:
            return False

        # 计算实际价格
        actual_price = self.calculate_actual_price_with_slippage(
            stock_code=stock_code,
            reference_price=cover_price,
            shares=short_pos.shares,
            is_buy=True,
            date=date
        )

        # 买券成本
        cover_amount = short_pos.shares * actual_price
        cover_costs = ShortSellingCosts.calculate_buy_to_cover_cost(
            amount=cover_amount,
            stock_code=stock_code,
            commission_rate=self.commission_rate,
            min_commission=self.min_commission,
            stamp_tax_rate=self.stamp_tax_rate
        )

        # 计算盈亏
        pnl = short_pos.calculate_profit_loss(actual_price, date)

        # 记录交易
        self.cost_analyzer.add_trade_from_dict(
            date=date,
            stock_code=stock_code,
            action='cover_short',
            shares=short_pos.shares,
            price=actual_price,
            commission=cover_costs['commission'],
            stamp_tax=cover_costs['stamp_tax'],
            slippage=short_pos.shares * (actual_price - cover_price)
        )

        # 更新组合：初始卖出金额 + 盈亏 - 买券成本
        portfolio.update_cash(short_pos.initial_amount + pnl['net_pnl'] - cover_amount - cover_costs['total_cost'])
        portfolio.remove_short_position(stock_code)

        return True
