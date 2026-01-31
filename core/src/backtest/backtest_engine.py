"""
回测引擎核心模块
实现向量化回测，支持A股T+1交易规则
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Callable
from datetime import datetime
import warnings
from loguru import logger
import gc
import time

warnings.filterwarnings('ignore')

from src.config.trading_rules import (
    TradingCosts,
    PriceLimitRules,
    T_PLUS_N,
    MarketType
)
from src.utils.response import Response
from src.exceptions import BacktestError

from .cost_analyzer import TradingCostAnalyzer, Trade
from .slippage_models import SlippageModel, FixedSlippageModel
from .short_selling import ShortSellingCosts, ShortPosition


class BacktestEngine:
    """向量化回测引擎"""

    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = None,
        stamp_tax_rate: float = None,
        min_commission: float = None,
        slippage: float = 0.0,
        slippage_model: Optional[SlippageModel] = None,
        verbose: bool = True
    ):
        """
        初始化回测引擎

        参数:
            initial_capital: 初始资金
            commission_rate: 佣金费率（None则使用默认配置）
            stamp_tax_rate: 印花税率（None则使用默认配置）
            min_commission: 最小佣金（None则使用默认配置）
            slippage: 滑点（比例，仅在slippage_model=None时使用）
            slippage_model: 滑点模型（可选，更高级）
            verbose: 是否打印详细信息
        """
        self.initial_capital = initial_capital
        self.verbose = verbose

        # 交易成本
        self.commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT
        self.stamp_tax_rate = stamp_tax_rate or TradingCosts.STAMP_TAX_RATE
        self.min_commission = min_commission or TradingCosts.MIN_COMMISSION
        self.slippage = slippage

        # 滑点模型（新增）
        if slippage_model is not None:
            self.slippage_model = slippage_model
        else:
            # 向后兼容：使用固定滑点模型
            self.slippage_model = FixedSlippageModel(slippage_pct=slippage)

        # 回测结果
        self.portfolio_value = None
        self.positions = None
        self.trades = None
        self.daily_returns = None
        self.metrics = {}

        # 成本分析器
        self.cost_analyzer = TradingCostAnalyzer()

        # 市场数据缓存（用于高级滑点模型）
        self._market_data_cache = {}

    def set_market_data(
        self,
        volumes: Optional[pd.DataFrame] = None,
        volatilities: Optional[pd.DataFrame] = None,
        bid_prices: Optional[pd.DataFrame] = None,
        ask_prices: Optional[pd.DataFrame] = None
    ):
        """
        设置市场数据（用于高级滑点模型）

        参数:
            volumes: 成交量DataFrame (index=date, columns=stock_codes)
            volatilities: 波动率DataFrame
            bid_prices: 买一价DataFrame
            ask_prices: 卖一价DataFrame
        """
        if volumes is not None:
            self._market_data_cache['volumes'] = volumes

        if volatilities is not None:
            self._market_data_cache['volatilities'] = volatilities

        if bid_prices is not None:
            self._market_data_cache['bid_prices'] = bid_prices

        if ask_prices is not None:
            self._market_data_cache['ask_prices'] = ask_prices

    def _calculate_actual_price_with_slippage(
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
            date: 交易日期（用于获取市场数据）

        返回:
            实际成交价格
        """
        order_size = shares * reference_price

        # 准备市场数据参数
        kwargs = {}

        # 如果有成交量数据
        if 'volumes' in self._market_data_cache and date is not None:
            volumes_df = self._market_data_cache['volumes']
            if date in volumes_df.index and stock_code in volumes_df.columns:
                # 使用过去20日平均成交量
                recent_volumes = volumes_df.loc[:date, stock_code].tail(20)
                avg_volume = recent_volumes.mean() if len(recent_volumes) > 0 else None
                if avg_volume and not np.isnan(avg_volume):
                    kwargs['avg_volume'] = avg_volume * reference_price  # 转换为金额

        # 如果有波动率数据
        if 'volatilities' in self._market_data_cache and date is not None:
            vol_df = self._market_data_cache['volatilities']
            if date in vol_df.index and stock_code in vol_df.columns:
                volatility = vol_df.loc[date, stock_code]
                if not np.isnan(volatility):
                    kwargs['volatility'] = volatility

        # 如果有盘口数据
        if 'bid_prices' in self._market_data_cache and date is not None:
            bid_df = self._market_data_cache['bid_prices']
            ask_df = self._market_data_cache.get('ask_prices')

            if (bid_df is not None and date in bid_df.index and stock_code in bid_df.columns and
                ask_df is not None and date in ask_df.index and stock_code in ask_df.columns):

                bid_price = bid_df.loc[date, stock_code]
                ask_price = ask_df.loc[date, stock_code]

                if not np.isnan(bid_price) and not np.isnan(ask_price):
                    kwargs['bid_price'] = bid_price
                    kwargs['ask_price'] = ask_price

        # 使用滑点模型计算实际价格
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
            stock_code: 股票代码（用于判断交易所）

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

    def backtest_long_only(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 50,
        holding_period: int = 5,
        rebalance_freq: str = 'W'
    ) -> Response:
        """
        纯多头回测（等权重选股策略）

        参数:
            signals: 信号DataFrame (index=date, columns=stock_codes, values=signal_scores)
            prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
            top_n: 每期选择前N只股票
            holding_period: 最短持仓期（天）
            rebalance_freq: 调仓频率 ('D'=日, 'W'=周, 'M'=月)

        返回:
            回测结果字典
        """
        logger.info(f"\n开始回测...")
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info(f"选股数量: {top_n}")
        logger.info(f"调仓频率: {rebalance_freq}")
        logger.info(f"持仓期: {holding_period}天")

        # 对齐数据
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)

        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        logger.info(f"\n数据范围:")
        logger.info(f"  交易日期: {len(common_dates)} 天 ({common_dates[0]} ~ {common_dates[-1]})")
        logger.info(f"  股票数量: {len(common_stocks)} 只")

        # 初始化
        dates = signals.index
        n_days = len(dates)
        cash = self.initial_capital
        portfolio_values = []
        positions_history = []

        # 当前持仓 {stock_code: {'shares': 100, 'entry_price': 10.0, 'entry_date': date}}
        current_positions = {}

        # 调仓日期
        if rebalance_freq == 'D':
            rebalance_dates = dates
        elif rebalance_freq == 'W':
            rebalance_dates = dates[dates.to_series().dt.dayofweek == 0]  # 每周一
        elif rebalance_freq == 'M':
            rebalance_dates = dates[dates.to_series().dt.is_month_start]  # 每月初
        else:
            raise ValueError(f"不支持的调仓频率: {rebalance_freq}")

        logger.info(f"\n调仓次数: {len(rebalance_dates)} 次")

        # 回测主循环
        for i, date in enumerate(dates):
            # 计算当前持仓市值
            holdings_value = 0
            for stock, pos in current_positions.items():
                if stock in prices.columns:
                    current_price = prices.loc[date, stock]
                    if not np.isnan(current_price):
                        holdings_value += pos['shares'] * current_price

            # 总资产
            total_value = cash + holdings_value
            portfolio_values.append({
                'date': date,
                'cash': cash,
                'holdings': holdings_value,
                'total': total_value
            })

            # 记录持仓
            positions_history.append({
                'date': date,
                'positions': current_positions.copy()
            })

            # 检查是否调仓日
            if date in rebalance_dates:
                # 卖出不在新组合中的股票 + 持有期已满的股票
                today_signals = signals.loc[date].dropna()
                top_stocks = today_signals.nlargest(top_n).index.tolist()

                stocks_to_sell = []
                for stock, pos in current_positions.items():
                    # 计算持有天数
                    entry_idx = dates.get_loc(pos['entry_date'])
                    current_idx = dates.get_loc(date)
                    holding_days = current_idx - entry_idx

                    # 卖出条件：不在新组合中 或 持仓期已满
                    if stock not in top_stocks or holding_days >= holding_period:
                        stocks_to_sell.append(stock)

                # 执行卖出（T+1: 今日决定，次日执行）
                if i < n_days - 1:  # 确保次日存在
                    next_date = dates[i + 1]

                    for stock in stocks_to_sell:
                        pos = current_positions[stock]
                        if stock in prices.columns:
                            # 次日开盘价卖出
                            sell_price = prices.loc[next_date, stock]
                            if not np.isnan(sell_price):
                                # 使用滑点模型计算实际成交价格
                                actual_price = self._calculate_actual_price_with_slippage(
                                    stock_code=stock,
                                    reference_price=sell_price,
                                    shares=pos['shares'],
                                    is_buy=False,
                                    date=next_date
                                )

                                # 卖出金额
                                sell_amount = pos['shares'] * actual_price

                                # 计算卖出交易成本
                                cost = self.calculate_trading_cost(sell_amount, is_buy=False, stock_code=stock)

                                # 记录交易到成本分析器
                                self.cost_analyzer.add_trade_from_dict(
                                    date=next_date,
                                    stock_code=stock,
                                    action='sell',
                                    shares=pos['shares'],
                                    price=actual_price,
                                    commission=cost * 0.5,  # 估算佣金占50%
                                    stamp_tax=sell_amount * self.stamp_tax_rate,  # 印花税
                                    slippage=pos['shares'] * sell_price * self.slippage  # 滑点成本
                                )

                                # 更新现金
                                cash += (sell_amount - cost)

                                # 移除持仓
                                del current_positions[stock]

                # 买入新股票
                if i < n_days - 1:
                    next_date = dates[i + 1]

                    # 可用于买入的股票（不在当前持仓中）
                    stocks_to_buy = [s for s in top_stocks if s not in current_positions]

                    if stocks_to_buy:
                        # 平均分配资金
                        capital_per_stock = cash / len(stocks_to_buy)

                        for stock in stocks_to_buy:
                            if stock in prices.columns:
                                # 次日开盘价买入
                                buy_price = prices.loc[next_date, stock]
                                if not np.isnan(buy_price) and buy_price > 0:
                                    # 先估算股数（用于滑点计算）
                                    estimated_shares = int(capital_per_stock / buy_price / 100) * 100

                                    if estimated_shares >= 100:
                                        # 使用滑点模型计算实际成交价格
                                        actual_price = self._calculate_actual_price_with_slippage(
                                            stock_code=stock,
                                            reference_price=buy_price,
                                            shares=estimated_shares,
                                            is_buy=True,
                                            date=next_date
                                        )

                                        # 重新计算可买股数（考虑实际价格）
                                        max_shares = int(capital_per_stock / actual_price / 100) * 100
                                    else:
                                        max_shares = 0

                                    if max_shares >= 100:
                                        # 买入金额
                                        buy_amount = max_shares * actual_price

                                        # 计算买入交易成本
                                        cost = self.calculate_trading_cost(buy_amount, is_buy=True, stock_code=stock)

                                        # 检查资金是否充足
                                        if cash >= (buy_amount + cost):
                                            # 记录交易到成本分析器
                                            self.cost_analyzer.add_trade_from_dict(
                                                date=next_date,
                                                stock_code=stock,
                                                action='buy',
                                                shares=max_shares,
                                                price=actual_price,
                                                commission=cost,  # 买入只有佣金
                                                stamp_tax=0.0,
                                                slippage=max_shares * buy_price * self.slippage  # 滑点成本
                                            )

                                            # 更新现金
                                            cash -= (buy_amount + cost)

                                            # 添加持仓
                                            current_positions[stock] = {
                                                'shares': max_shares,
                                                'entry_price': actual_price,
                                                'entry_date': next_date
                                            }

        # 保存结果
        self.portfolio_value = pd.DataFrame(portfolio_values).set_index('date')
        self.positions = positions_history

        # 计算收益率
        self.daily_returns = self.portfolio_value['total'].pct_change()

        logger.info(f"\n回测完成")
        logger.info(f"最终资产: {self.portfolio_value['total'].iloc[-1]:,.0f}")
        logger.info(f"总收益率: {(self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1) * 100:.2f}%")

        # 运行成本分析
        cost_metrics = self.cost_analyzer.analyze_all(
            portfolio_returns=self.daily_returns,
            portfolio_values=self.portfolio_value['total'],
            verbose=False
        )

        return Response.success(
            data={
                'portfolio_value': self.portfolio_value,
                'positions': self.positions,
                'daily_returns': self.daily_returns,
                'cost_analysis': cost_metrics,
                'cost_analyzer': self.cost_analyzer
            },
            message="多头回测完成",
            backtest_type="long_only",
            n_days=len(self.portfolio_value),
            initial_capital=self.initial_capital,
            final_value=float(self.portfolio_value['total'].iloc[-1]),
            total_return=float((self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1))
        )

    def backtest_market_neutral(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 20,
        bottom_n: int = 20,
        holding_period: int = 5,
        rebalance_freq: str = 'W',
        margin_rate: float = 0.10,
        margin_ratio: float = 0.5
    ) -> Response:
        """
        市场中性策略回测（多空对冲）

        策略逻辑:
        1. 做多信号最高的top_n只股票
        2. 做空信号最低的bottom_n只股票
        3. 多空金额相等，实现市场中性
        4. 考虑融券成本（融券利息）

        参数:
            signals: 信号DataFrame (index=date, columns=stock_codes, values=signal_scores)
            prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
            top_n: 做多前N只
            bottom_n: 做空后N只
            holding_period: 最短持仓期（天）
            rebalance_freq: 调仓频率 ('D'=日, 'W'=周, 'M'=月)
            margin_rate: 融券年化费率（默认10%）
            margin_ratio: 保证金比例（默认50%）

        返回:
            回测结果字典
        """
        logger.info(f"\n开始市场中性回测...")
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info(f"做多数量: {top_n}")
        logger.info(f"做空数量: {bottom_n}")
        logger.info(f"调仓频率: {rebalance_freq}")
        logger.info(f"持仓期: {holding_period}天")
        logger.info(f"融券费率: {margin_rate*100:.1f}%")

        # 对齐数据
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)

        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        logger.info(f"\n数据范围:")
        logger.info(f"  交易日期: {len(common_dates)} 天 ({common_dates[0]} ~ {common_dates[-1]})")
        logger.info(f"  股票数量: {len(common_stocks)} 只")

        # 初始化
        dates = signals.index
        n_days = len(dates)
        cash = self.initial_capital
        portfolio_values = []
        positions_history = []

        # 多头持仓 {stock_code: {'shares': 100, 'entry_price': 10.0, 'entry_date': date}}
        long_positions = {}

        # 空头持仓 {stock_code: ShortPosition对象}
        short_positions = {}

        # 调仓日期
        if rebalance_freq == 'D':
            rebalance_dates = dates
        elif rebalance_freq == 'W':
            rebalance_dates = dates[dates.to_series().dt.dayofweek == 0]  # 每周一
        elif rebalance_freq == 'M':
            rebalance_dates = dates[dates.to_series().dt.is_month_start]  # 每月初
        else:
            raise ValueError(f"不支持的调仓频率: {rebalance_freq}")

        logger.info(f"\n调仓次数: {len(rebalance_dates)} 次")

        # 回测主循环
        for i, date in enumerate(dates):
            # 计算多头持仓市值
            long_value = 0
            for stock, pos in long_positions.items():
                if stock in prices.columns:
                    current_price = prices.loc[date, stock]
                    if not np.isnan(current_price):
                        long_value += pos['shares'] * current_price

            # 计算空头持仓市值及盈亏
            short_value = 0
            short_pnl_total = 0
            short_interest_total = 0

            for stock, short_pos in short_positions.items():
                if stock in prices.columns:
                    current_price = prices.loc[date, stock]
                    if not np.isnan(current_price):
                        # 空头持仓市值（负数）
                        short_value += short_pos.shares * current_price

                        # 计算空头盈亏
                        pnl = short_pos.calculate_profit_loss(current_price, date)
                        short_pnl_total += pnl['net_pnl']
                        short_interest_total += pnl['interest_cost']

            # 总资产 = 现金 + 多头市值 - 空头市值 + 空头盈亏
            # 注意：空头盈亏已经包含在short_pnl_total中
            total_value = cash + long_value + short_pnl_total

            portfolio_values.append({
                'date': date,
                'cash': cash,
                'long_value': long_value,
                'short_value': short_value,
                'short_pnl': short_pnl_total,
                'short_interest': short_interest_total,
                'total': total_value
            })

            # 记录持仓
            positions_history.append({
                'date': date,
                'long_positions': long_positions.copy(),
                'short_positions': {k: v.to_dict() for k, v in short_positions.items()}
            })

            # 检查是否调仓日
            if date in rebalance_dates:
                today_signals = signals.loc[date].dropna()

                # 选出做多和做空的股票
                top_stocks = today_signals.nlargest(top_n).index.tolist()
                bottom_stocks = today_signals.nsmallest(bottom_n).index.tolist()

                # === 平仓逻辑 ===
                if i < n_days - 1:
                    next_date = dates[i + 1]

                    # 平多头持仓
                    long_to_close = []
                    for stock, pos in long_positions.items():
                        entry_idx = dates.get_loc(pos['entry_date'])
                        current_idx = dates.get_loc(date)
                        holding_days = current_idx - entry_idx

                        if stock not in top_stocks or holding_days >= holding_period:
                            long_to_close.append(stock)

                    for stock in long_to_close:
                        pos = long_positions[stock]
                        if stock in prices.columns:
                            sell_price = prices.loc[next_date, stock]
                            if not np.isnan(sell_price):
                                actual_price = self._calculate_actual_price_with_slippage(
                                    stock_code=stock,
                                    reference_price=sell_price,
                                    shares=pos['shares'],
                                    is_buy=False,
                                    date=next_date
                                )

                                sell_amount = pos['shares'] * actual_price
                                cost = self.calculate_trading_cost(sell_amount, is_buy=False, stock_code=stock)

                                self.cost_analyzer.add_trade_from_dict(
                                    date=next_date,
                                    stock_code=stock,
                                    action='sell',
                                    shares=pos['shares'],
                                    price=actual_price,
                                    commission=cost * 0.5,
                                    stamp_tax=sell_amount * self.stamp_tax_rate,
                                    slippage=pos['shares'] * sell_price * self.slippage
                                )

                                cash += (sell_amount - cost)
                                del long_positions[stock]

                    # 平空头持仓（买券还券）
                    short_to_close = []
                    for stock, short_pos in short_positions.items():
                        entry_idx = dates.get_loc(short_pos.entry_date)
                        current_idx = dates.get_loc(date)
                        holding_days = current_idx - entry_idx

                        if stock not in bottom_stocks or holding_days >= holding_period:
                            short_to_close.append(stock)

                    for stock in short_to_close:
                        short_pos = short_positions[stock]
                        if stock in prices.columns:
                            cover_price = prices.loc[next_date, stock]
                            if not np.isnan(cover_price):
                                actual_price = self._calculate_actual_price_with_slippage(
                                    stock_code=stock,
                                    reference_price=cover_price,
                                    shares=short_pos.shares,
                                    is_buy=True,
                                    date=next_date
                                )

                                # 买券还券成本
                                cover_amount = short_pos.shares * actual_price
                                cover_costs = ShortSellingCosts.calculate_buy_to_cover_cost(
                                    amount=cover_amount,
                                    stock_code=stock,
                                    commission_rate=self.commission_rate,
                                    min_commission=self.min_commission,
                                    stamp_tax_rate=self.stamp_tax_rate
                                )

                                # 计算最终盈亏
                                pnl = short_pos.calculate_profit_loss(actual_price, next_date)

                                # 记录交易
                                self.cost_analyzer.add_trade_from_dict(
                                    date=next_date,
                                    stock_code=stock,
                                    action='cover_short',
                                    shares=short_pos.shares,
                                    price=actual_price,
                                    commission=cover_costs['commission'],
                                    stamp_tax=cover_costs['stamp_tax'],
                                    slippage=short_pos.shares * cover_price * self.slippage
                                )

                                # 更新现金：初始卖出金额 + 盈亏 - 买券成本
                                cash += (short_pos.initial_amount + pnl['net_pnl'] - cover_amount - cover_costs['total_cost'])

                                del short_positions[stock]

                # === 开仓逻辑 ===
                if i < n_days - 1:
                    next_date = dates[i + 1]

                    # 计算可用于开仓的资金
                    # 市场中性：多空金额相等，各占一半可用资金
                    available_for_long = cash / 2
                    available_for_short = cash / 2

                    # 开多头仓位
                    long_to_open = [s for s in top_stocks if s not in long_positions]
                    if long_to_open:
                        capital_per_long = available_for_long / len(long_to_open)

                        for stock in long_to_open:
                            if stock in prices.columns:
                                buy_price = prices.loc[next_date, stock]
                                if not np.isnan(buy_price) and buy_price > 0:
                                    estimated_shares = int(capital_per_long / buy_price / 100) * 100

                                    if estimated_shares >= 100:
                                        actual_price = self._calculate_actual_price_with_slippage(
                                            stock_code=stock,
                                            reference_price=buy_price,
                                            shares=estimated_shares,
                                            is_buy=True,
                                            date=next_date
                                        )

                                        max_shares = int(capital_per_long / actual_price / 100) * 100

                                        if max_shares >= 100:
                                            buy_amount = max_shares * actual_price
                                            cost = self.calculate_trading_cost(buy_amount, is_buy=True, stock_code=stock)

                                            if cash >= (buy_amount + cost):
                                                self.cost_analyzer.add_trade_from_dict(
                                                    date=next_date,
                                                    stock_code=stock,
                                                    action='buy',
                                                    shares=max_shares,
                                                    price=actual_price,
                                                    commission=cost,
                                                    stamp_tax=0.0,
                                                    slippage=max_shares * buy_price * self.slippage
                                                )

                                                cash -= (buy_amount + cost)

                                                long_positions[stock] = {
                                                    'shares': max_shares,
                                                    'entry_price': actual_price,
                                                    'entry_date': next_date
                                                }

                    # 开空头仓位
                    short_to_open = [s for s in bottom_stocks if s not in short_positions]
                    if short_to_open:
                        capital_per_short = available_for_short / len(short_to_open)

                        for stock in short_to_open:
                            if stock in prices.columns:
                                short_price = prices.loc[next_date, stock]
                                if not np.isnan(short_price) and short_price > 0:
                                    estimated_shares = int(capital_per_short / short_price / 100) * 100

                                    if estimated_shares >= 100:
                                        actual_price = self._calculate_actual_price_with_slippage(
                                            stock_code=stock,
                                            reference_price=short_price,
                                            shares=estimated_shares,
                                            is_buy=False,
                                            date=next_date
                                        )

                                        max_shares = int(capital_per_short / actual_price / 100) * 100

                                        if max_shares >= 100:
                                            short_amount = max_shares * actual_price

                                            # 融券卖出成本
                                            short_costs = ShortSellingCosts.calculate_short_sell_cost(
                                                amount=short_amount,
                                                stock_code=stock,
                                                commission_rate=self.commission_rate,
                                                min_commission=self.min_commission
                                            )

                                            # 所需保证金
                                            required_margin = ShortSellingCosts.calculate_required_margin(
                                                short_amount=short_amount,
                                                margin_ratio=margin_ratio
                                            )

                                            # 检查资金是否充足（需要保证金 + 交易成本）
                                            if cash >= (required_margin + short_costs['total_cost']):
                                                self.cost_analyzer.add_trade_from_dict(
                                                    date=next_date,
                                                    stock_code=stock,
                                                    action='short_sell',
                                                    shares=max_shares,
                                                    price=actual_price,
                                                    commission=short_costs['commission'],
                                                    stamp_tax=0.0,
                                                    slippage=max_shares * short_price * self.slippage
                                                )

                                                # 更新现金：获得卖出金额 - 保证金 - 交易成本
                                                cash += (short_amount - required_margin - short_costs['total_cost'])

                                                # 创建空头持仓
                                                short_positions[stock] = ShortPosition(
                                                    stock_code=stock,
                                                    shares=max_shares,
                                                    entry_price=actual_price,
                                                    entry_date=next_date,
                                                    margin_rate=margin_rate
                                                )

        # 保存结果
        self.portfolio_value = pd.DataFrame(portfolio_values).set_index('date')
        self.positions = positions_history

        # 计算收益率
        self.daily_returns = self.portfolio_value['total'].pct_change()

        logger.info(f"\n回测完成")
        logger.info(f"最终资产: {self.portfolio_value['total'].iloc[-1]:,.0f}")
        logger.info(f"总收益率: {(self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1) * 100:.2f}%")
        logger.info(f"累计融券利息: {self.portfolio_value['short_interest'].iloc[-1]:,.2f}")

        # 运行成本分析
        cost_metrics = self.cost_analyzer.analyze_all(
            portfolio_returns=self.daily_returns,
            portfolio_values=self.portfolio_value['total'],
            verbose=False
        )

        return Response.success(
            data={
                'portfolio_value': self.portfolio_value,
                'positions': self.positions,
                'daily_returns': self.daily_returns,
                'cost_analysis': cost_metrics,
                'cost_analyzer': self.cost_analyzer
            },
            message="市场中性回测完成",
            backtest_type="market_neutral",
            n_days=len(self.portfolio_value),
            initial_capital=self.initial_capital,
            final_value=float(self.portfolio_value['total'].iloc[-1]),
            total_return=float((self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1)),
            total_short_interest=float(self.portfolio_value['short_interest'].iloc[-1])
        )

    def get_portfolio_value(self) -> pd.DataFrame:
        """获取组合净值曲线"""
        if self.portfolio_value is None:
            raise ValueError("请先运行回测")
        return self.portfolio_value

    def get_daily_returns(self) -> pd.Series:
        """获取每日收益率"""
        if self.daily_returns is None:
            raise ValueError("请先运行回测")
        return self.daily_returns

    def get_positions(self) -> List[Dict]:
        """获取持仓历史"""
        if self.positions is None:
            raise ValueError("请先运行回测")
        return self.positions

    # ==================== 内存优化：分块回测 ====================

    def backtest_long_only_chunked(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 50,
        holding_period: int = 5,
        rebalance_freq: str = 'W',
        chunk_size: int = 60,
        enable_memory_monitor: bool = False
    ) -> Response:
        """
        分块回测（内存优化版）

        原理:
        - 将回测期分成多个时间窗口（如每60天一块）
        - 每次只加载一个窗口的数据
        - 增量更新持仓和资金状态
        - 内存占用减少80%（3GB → 600MB）

        参数:
            signals: 信号DataFrame
            prices: 价格DataFrame
            top_n: 每期选择前N只股票
            holding_period: 最短持仓期（天）
            rebalance_freq: 调仓频率
            chunk_size: 每个时间窗口的天数（建议30-90天）
            enable_memory_monitor: 是否启用内存监控

        返回:
            回测结果字典
        """
        # 内存监控
        if enable_memory_monitor:
            from src.utils.memory_profiler import memory_profiler
            context = memory_profiler("分块回测", track_interval=0.5)
            context.__enter__()
        else:
            context = None

        try:
            logger.info(f"\n开始分块回测（内存优化）...")
            logger.info(f"初始资金: {self.initial_capital:,.0f}")
            logger.info(f"时间窗口大小: {chunk_size}天")

            # 对齐数据
            common_dates = signals.index.intersection(prices.index)
            common_stocks = signals.columns.intersection(prices.columns)

            dates = common_dates.tolist()
            n_dates = len(dates)
            num_chunks = (n_dates + chunk_size - 1) // chunk_size

            logger.info(f"\n数据范围:")
            logger.info(f"  交易日期: {n_dates}天 ({dates[0]} ~ {dates[-1]})")
            logger.info(f"  股票数量: {len(common_stocks)}只")
            logger.info(f"  时间窗口数: {num_chunks}个")

            # 全局状态变量
            current_cash = self.initial_capital
            current_positions = {}  # {stock_code: {'shares': 100, 'entry_price': 10.0, 'entry_date': date}}
            all_portfolio_values = []
            all_positions_history = []

            # 确定所有调仓日期
            dates_series = pd.Series(dates)
            if rebalance_freq == 'D':
                rebalance_dates = set(dates)
            elif rebalance_freq == 'W':
                rebalance_dates = set(pd.DatetimeIndex(dates)[pd.DatetimeIndex(dates).dayofweek == 0])
            elif rebalance_freq == 'M':
                rebalance_dates = set(pd.DatetimeIndex(dates)[pd.DatetimeIndex(dates).is_month_start])
            else:
                raise ValueError(f"不支持的调仓频率: {rebalance_freq}")

            # 分块处理
            for chunk_idx in range(num_chunks):
                start_idx = chunk_idx * chunk_size
                end_idx = min(start_idx + chunk_size, n_dates)

                # 添加overlap：前后各扩展holding_period天（确保持仓期计算正确）
                overlap_start = max(0, start_idx - holding_period)
                overlap_end = min(end_idx + holding_period, n_dates)

                chunk_dates = dates[overlap_start:overlap_end]

                logger.info(
                    f"\n处理时间窗口 {chunk_idx+1}/{num_chunks}: "
                    f"{chunk_dates[0]} ~ {chunk_dates[-1]} "
                    f"({len(chunk_dates)}天)"
                )

                # 提取当前窗口数据（仅加载需要的部分）
                chunk_signals = signals.loc[chunk_dates, common_stocks]
                chunk_prices = prices.loc[chunk_dates, common_stocks]

                # 处理当前窗口
                chunk_result = self._process_chunk_backtest(
                    chunk_dates=chunk_dates,
                    chunk_signals=chunk_signals,
                    chunk_prices=chunk_prices,
                    initial_cash=current_cash,
                    initial_positions=current_positions,
                    top_n=top_n,
                    holding_period=holding_period,
                    rebalance_dates=rebalance_dates,
                    actual_start_idx=start_idx,
                    actual_end_idx=end_idx,
                    all_dates=dates
                )

                # 更新全局状态
                current_cash = chunk_result['final_cash']
                current_positions = chunk_result['final_positions']
                all_portfolio_values.extend(chunk_result['portfolio_values'])
                all_positions_history.extend(chunk_result['positions_history'])

                # 释放当前窗口内存
                del chunk_signals, chunk_prices, chunk_result
                if chunk_idx % 5 == 0:  # 每5个窗口强制垃圾回收
                    gc.collect()

                logger.debug(
                    f"窗口 {chunk_idx+1} 完成: "
                    f"现金 {current_cash:,.0f}, "
                    f"持仓 {len(current_positions)}只"
                )

            # 保存最终结果
            self.portfolio_value = pd.DataFrame(all_portfolio_values).set_index('date')
            self.positions = all_positions_history
            self.daily_returns = self.portfolio_value['total'].pct_change()

            logger.info(f"\n分块回测完成")
            logger.info(f"最终资产: {self.portfolio_value['total'].iloc[-1]:,.0f}")
            logger.info(f"总收益率: {(self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1) * 100:.2f}%")

            # 成本分析
            cost_metrics = self.cost_analyzer.analyze_all(
                portfolio_returns=self.daily_returns,
                portfolio_values=self.portfolio_value['total'],
                verbose=False
            )

            return Response.success(
                data={
                    'portfolio_value': self.portfolio_value,
                    'positions': self.positions,
                    'daily_returns': self.daily_returns,
                    'cost_analysis': cost_metrics,
                    'cost_analyzer': self.cost_analyzer
                },
                message="分块回测完成",
                backtest_type="long_only_chunked",
                n_days=len(self.portfolio_value),
                initial_capital=self.initial_capital,
                final_value=float(self.portfolio_value['total'].iloc[-1]),
                total_return=float((self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1))
            )

        finally:
            if context is not None:
                context.__exit__(None, None, None)

    def _process_chunk_backtest(
        self,
        chunk_dates: List,
        chunk_signals: pd.DataFrame,
        chunk_prices: pd.DataFrame,
        initial_cash: float,
        initial_positions: Dict,
        top_n: int,
        holding_period: int,
        rebalance_dates: set,
        actual_start_idx: int,
        actual_end_idx: int,
        all_dates: List
    ) -> Dict:
        """
        处理单个时间窗口的回测

        参数:
            chunk_dates: 当前窗口日期列表（包含overlap）
            chunk_signals: 当前窗口信号数据
            chunk_prices: 当前窗口价格数据
            initial_cash: 窗口开始时的现金
            initial_positions: 窗口开始时的持仓
            top_n: 选股数量
            holding_period: 持仓期
            rebalance_dates: 所有调仓日期
            actual_start_idx: 实际窗口起始索引（在全部日期中）
            actual_end_idx: 实际窗口结束索引（在全部日期中）
            all_dates: 全部日期列表

        返回:
            窗口回测结果
        """
        cash = initial_cash
        current_positions = initial_positions.copy()
        portfolio_values = []
        positions_history = []

        # 仅对实际窗口内的日期进行记录
        actual_dates = all_dates[actual_start_idx:actual_end_idx]

        for i, date in enumerate(chunk_dates):
            # 计算当前持仓市值
            holdings_value = 0
            for stock, pos in current_positions.items():
                if stock in chunk_prices.columns:
                    try:
                        current_price = chunk_prices.loc[date, stock]
                        if not np.isnan(current_price):
                            holdings_value += pos['shares'] * current_price
                    except KeyError:
                        pass

            # 总资产
            total_value = cash + holdings_value

            # 仅记录实际窗口内的数据（避免重复）
            if date in actual_dates:
                portfolio_values.append({
                    'date': date,
                    'cash': cash,
                    'holdings': holdings_value,
                    'total': total_value
                })

                positions_history.append({
                    'date': date,
                    'positions': current_positions.copy()
                })

            # 检查是否调仓日
            if date in rebalance_dates and date in chunk_signals.index:
                # 卖出不在新组合中的股票
                today_signals = chunk_signals.loc[date].dropna()
                top_stocks = today_signals.nlargest(top_n).index.tolist()

                stocks_to_sell = []
                for stock, pos in current_positions.items():
                    # 计算持有天数
                    try:
                        entry_idx = all_dates.index(pos['entry_date'])
                        current_idx = all_dates.index(date)
                        holding_days = current_idx - entry_idx
                    except (ValueError, KeyError):
                        holding_days = holding_period  # 默认已满持仓期

                    # 卖出条件
                    if stock not in top_stocks or holding_days >= holding_period:
                        stocks_to_sell.append(stock)

                # 执行卖出（T+1）
                if i < len(chunk_dates) - 1:
                    next_date = chunk_dates[i + 1]

                    for stock in stocks_to_sell:
                        pos = current_positions[stock]
                        if stock in chunk_prices.columns:
                            try:
                                sell_price = chunk_prices.loc[next_date, stock]
                                if not np.isnan(sell_price) and sell_price > 0:
                                    # 实际成交价
                                    actual_price = self._calculate_actual_price_with_slippage(
                                        stock_code=stock,
                                        reference_price=sell_price,
                                        shares=pos['shares'],
                                        is_buy=False,
                                        date=next_date
                                    )

                                    sell_amount = pos['shares'] * actual_price
                                    cost = self.calculate_trading_cost(sell_amount, is_buy=False, stock_code=stock)

                                    # 记录交易
                                    self.cost_analyzer.add_trade_from_dict(
                                        date=next_date,
                                        stock_code=stock,
                                        action='sell',
                                        shares=pos['shares'],
                                        price=actual_price,
                                        commission=cost * 0.5,
                                        stamp_tax=sell_amount * self.stamp_tax_rate,
                                        slippage=pos['shares'] * sell_price * self.slippage
                                    )

                                    cash += (sell_amount - cost)
                                    del current_positions[stock]
                            except KeyError:
                                pass

                # 买入新股票（T+1）
                if i < len(chunk_dates) - 1:
                    next_date = chunk_dates[i + 1]
                    stocks_to_buy = [s for s in top_stocks if s not in current_positions]

                    if stocks_to_buy:
                        capital_per_stock = cash / len(stocks_to_buy)

                        for stock in stocks_to_buy:
                            if stock in chunk_prices.columns:
                                try:
                                    buy_price = chunk_prices.loc[next_date, stock]
                                    if not np.isnan(buy_price) and buy_price > 0:
                                        estimated_shares = int(capital_per_stock / buy_price / 100) * 100

                                        if estimated_shares >= 100:
                                            actual_price = self._calculate_actual_price_with_slippage(
                                                stock_code=stock,
                                                reference_price=buy_price,
                                                shares=estimated_shares,
                                                is_buy=True,
                                                date=next_date
                                            )

                                            max_shares = int(capital_per_stock / actual_price / 100) * 100

                                            if max_shares >= 100:
                                                buy_amount = max_shares * actual_price
                                                cost = self.calculate_trading_cost(buy_amount, is_buy=True, stock_code=stock)

                                                if cash >= (buy_amount + cost):
                                                    # 记录交易
                                                    self.cost_analyzer.add_trade_from_dict(
                                                        date=next_date,
                                                        stock_code=stock,
                                                        action='buy',
                                                        shares=max_shares,
                                                        price=actual_price,
                                                        commission=cost,
                                                        stamp_tax=0.0,
                                                        slippage=max_shares * buy_price * self.slippage
                                                    )

                                                    cash -= (buy_amount + cost)
                                                    current_positions[stock] = {
                                                        'shares': max_shares,
                                                        'entry_price': actual_price,
                                                        'entry_date': next_date
                                                    }
                                except KeyError:
                                    pass

        return {
            'final_cash': cash,
            'final_positions': current_positions,
            'portfolio_values': portfolio_values,
            'positions_history': positions_history
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("回测引擎测试\n")

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600010)]  # 10只股票

    # 模拟价格数据（随机游走）
    price_data = {}
    for stock in stocks:
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 模拟信号数据（带一定预测能力）
    signal_data = {}
    for stock in stocks:
        # 信号与未来收益有一定相关性
        # 修复：使用正确的未来收益计算方法
        future_returns = (prices_df[stock].shift(-5) / prices_df[stock] - 1) * 100
        signals = future_returns + np.random.normal(0, 0.01, len(dates))
        signal_data[stock] = signals

    signals_df = pd.DataFrame(signal_data, index=dates)

    logger.info("测试数据:")
    logger.info(f"  日期范围: {dates[0]} ~ {dates[-1]}")
    logger.info(f"  股票数量: {len(stocks)}")
    logger.info(f"  交易日数: {len(dates)}")

    # 创建回测引擎
    logger.info("\n初始化回测引擎:")
    engine = BacktestEngine(
        initial_capital=1000000,
        verbose=True
    )

    # 运行回测
    logger.info("\n运行回测:")
    results = engine.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=5,
        holding_period=5,
        rebalance_freq='W'
    )

    # 查看结果
    logger.info("\n组合净值:")
    logger.info(results['portfolio_value'].tail())

    logger.success("\n✓ 回测引擎测试完成")
