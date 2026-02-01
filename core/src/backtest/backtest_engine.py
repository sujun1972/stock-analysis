"""
回测引擎核心模块
实现向量化回测，支持A股T+1交易规则
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime
import warnings
from loguru import logger
import gc

warnings.filterwarnings('ignore')

from src.config.trading_rules import TradingCosts
from src.utils.response import Response

from .cost_analyzer import TradingCostAnalyzer
from .slippage_models import SlippageModel, FixedSlippageModel
from .backtest_portfolio import BacktestPortfolio
from .backtest_executor import BacktestExecutor
from .backtest_recorder import BacktestRecorder


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
        self.initial_capital = initial_capital
        self.verbose = verbose

        # 交易成本
        self.commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT
        self.stamp_tax_rate = stamp_tax_rate or TradingCosts.STAMP_TAX_RATE
        self.min_commission = min_commission or TradingCosts.MIN_COMMISSION
        self.slippage = slippage  # 向后兼容

        # 滑点模型
        self.slippage_model = slippage_model or FixedSlippageModel(slippage_pct=slippage)

        # 市场数据缓存
        self._market_data_cache = {}

        # 成本分析器
        self.cost_analyzer = TradingCostAnalyzer()

        # 交易执行器
        self.executor = BacktestExecutor(
            commission_rate=self.commission_rate,
            stamp_tax_rate=self.stamp_tax_rate,
            min_commission=self.min_commission,
            slippage_model=self.slippage_model,
            cost_analyzer=self.cost_analyzer,
            market_data_cache=self._market_data_cache
        )

        # 回测结果（兼容原API）
        self.portfolio_value = None
        self.positions = None
        self.daily_returns = None
        self.metrics = {}

    def set_market_data(
        self,
        volumes: Optional[pd.DataFrame] = None,
        volatilities: Optional[pd.DataFrame] = None,
        bid_prices: Optional[pd.DataFrame] = None,
        ask_prices: Optional[pd.DataFrame] = None
    ):
        """设置市场数据（用于高级滑点模型）"""
        if volumes is not None:
            self._market_data_cache['volumes'] = volumes
        if volatilities is not None:
            self._market_data_cache['volatilities'] = volatilities
        if bid_prices is not None:
            self._market_data_cache['bid_prices'] = bid_prices
        if ask_prices is not None:
            self._market_data_cache['ask_prices'] = ask_prices

    def calculate_trading_cost(
        self,
        amount: float,
        is_buy: bool,
        stock_code: str = None
    ) -> float:
        """
        计算交易成本（向后兼容方法）

        参数:
            amount: 交易金额
            is_buy: 是否买入
            stock_code: 股票代码

        返回:
            交易成本
        """
        return self.executor.calculate_trading_cost(amount, is_buy, stock_code)

    def backtest_long_only(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 50,
        holding_period: int = 5,
        rebalance_freq: str = 'W'
    ) -> Response:
        """纯多头回测（等权重选股策略）"""
        logger.info(f"\n开始回测...")
        logger.info(f"初始资金: {self.initial_capital:,.0f}, 选股: {top_n}只, 调仓: {rebalance_freq}")

        # 对齐数据
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)
        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        logger.info(f"数据范围: {len(common_dates)}天, {len(common_stocks)}只股票")

        # 初始化组合和记录器
        portfolio = BacktestPortfolio(self.initial_capital)
        recorder = BacktestRecorder()

        # 调仓日期
        dates = signals.index
        rebalance_dates = self._get_rebalance_dates(dates, rebalance_freq)

        # 回测主循环
        for i, date in enumerate(dates):
            # 记录当前净值
            holdings_value = portfolio.calculate_long_holdings_value(prices, date)
            recorder.record_portfolio_value(
                date, portfolio.get_cash(), holdings_value, portfolio.get_cash() + holdings_value
            )
            recorder.record_positions(date, portfolio.get_long_only_snapshot())

            # 调仓
            if date in rebalance_dates and i < len(dates) - 1:
                self._rebalance_long_only(
                    portfolio, signals, prices, date, dates[i + 1], top_n, holding_period, dates
                )

        # 保存结果
        self.portfolio_value = recorder.get_portfolio_value_df()
        self.positions = recorder.get_positions_history()
        self.daily_returns = recorder.calculate_daily_returns()

        logger.info(f"回测完成: 最终资产 {self.portfolio_value['total'].iloc[-1]:,.0f}")

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
        """市场中性策略回测（多空对冲）"""
        logger.info(f"\n开始市场中性回测: 做多{top_n}只, 做空{bottom_n}只")

        # 对齐数据
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)
        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        # 初始化
        portfolio = BacktestPortfolio(self.initial_capital)
        recorder = BacktestRecorder()
        dates = signals.index
        rebalance_dates = self._get_rebalance_dates(dates, rebalance_freq)

        # 回测主循环
        for i, date in enumerate(dates):
            value_metrics = portfolio.get_total_value(prices, date)
            recorder.record_market_neutral_value(
                date, value_metrics['cash'], value_metrics['long_value'],
                value_metrics['short_value'], value_metrics['short_pnl'],
                value_metrics['short_interest'], value_metrics['total']
            )
            recorder.record_positions(date, portfolio.get_positions_snapshot())

            if date in rebalance_dates and i < len(dates) - 1:
                self._rebalance_market_neutral(
                    portfolio, signals, prices, date, dates[i + 1],
                    top_n, bottom_n, holding_period, dates, margin_rate, margin_ratio
                )

        # 保存结果
        self.portfolio_value = recorder.get_portfolio_value_df()
        self.positions = recorder.get_positions_history()
        self.daily_returns = recorder.calculate_daily_returns()

        logger.info(f"回测完成: 最终资产 {self.portfolio_value['total'].iloc[-1]:,.0f}")

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
        """分块回测（内存优化版）"""
        context = None
        if enable_memory_monitor:
            from src.utils.memory_profiler import memory_profiler
            context = memory_profiler("分块回测", track_interval=0.5)
            context.__enter__()

        try:
            logger.info(f"\n分块回测: {chunk_size}天/窗口")

            # 对齐数据
            common_dates = signals.index.intersection(prices.index)
            common_stocks = signals.columns.intersection(prices.columns)
            dates = common_dates.tolist()
            n_dates = len(dates)
            num_chunks = (n_dates + chunk_size - 1) // chunk_size

            # 初始化
            portfolio = BacktestPortfolio(self.initial_capital)
            recorder = BacktestRecorder()
            rebalance_dates = set(self._get_rebalance_dates(pd.DatetimeIndex(dates), rebalance_freq))

            # 分块处理
            for chunk_idx in range(num_chunks):
                start_idx = chunk_idx * chunk_size
                end_idx = min(start_idx + chunk_size, n_dates)
                overlap_start = max(0, start_idx - holding_period)
                overlap_end = min(end_idx + holding_period, n_dates)
                chunk_dates = dates[overlap_start:overlap_end]

                chunk_signals = signals.loc[chunk_dates, common_stocks]
                chunk_prices = prices.loc[chunk_dates, common_stocks]

                self._process_chunk(
                    chunk_dates, chunk_signals, chunk_prices, portfolio, recorder,
                    top_n, holding_period, rebalance_dates, start_idx, end_idx, dates
                )

                del chunk_signals, chunk_prices
                if chunk_idx % 5 == 0:
                    gc.collect()

            # 保存结果
            self.portfolio_value = recorder.get_portfolio_value_df()
            self.positions = recorder.get_positions_history()
            self.daily_returns = recorder.calculate_daily_returns()

            logger.info(f"分块回测完成: {self.portfolio_value['total'].iloc[-1]:,.0f}")

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

    # ==================== 私有辅助方法 ====================

    def _get_rebalance_dates(self, dates: pd.DatetimeIndex, freq: str):
        if freq == 'D':
            return dates
        elif freq == 'W':
            return dates[dates.to_series().dt.dayofweek == 0]
        elif freq == 'M':
            return dates[dates.to_series().dt.is_month_start]
        raise ValueError(f"不支持的调仓频率: {freq}")

    def _rebalance_long_only(
        self, portfolio, signals, prices, date, next_date, top_n, holding_period, all_dates
    ):
        # 选股
        top_stocks = signals.loc[date].dropna().nlargest(top_n).index.tolist()

        # 卖出
        for stock in portfolio.get_long_stocks_to_sell(top_stocks, date, holding_period, all_dates):
            if stock in prices.columns:
                sell_price = prices.loc[next_date, stock]
                if not np.isnan(sell_price):
                    self.executor.execute_sell(portfolio, stock, sell_price, next_date)

        # 买入
        stocks_to_buy = portfolio.get_stocks_to_buy(top_stocks)
        if stocks_to_buy:
            capital_per_stock = portfolio.get_cash() / len(stocks_to_buy)
            for stock in stocks_to_buy:
                if stock in prices.columns:
                    buy_price = prices.loc[next_date, stock]
                    if not np.isnan(buy_price) and buy_price > 0:
                        self.executor.execute_buy(portfolio, stock, buy_price, capital_per_stock, next_date)

    def _rebalance_market_neutral(
        self, portfolio, signals, prices, date, next_date,
        top_n, bottom_n, holding_period, all_dates, margin_rate, margin_ratio
    ):
        # 选股
        today_signals = signals.loc[date].dropna()
        top_stocks = today_signals.nlargest(top_n).index.tolist()
        bottom_stocks = today_signals.nsmallest(bottom_n).index.tolist()

        # 平多头
        for stock in portfolio.get_long_stocks_to_sell(top_stocks, date, holding_period, all_dates):
            if stock in prices.columns and not np.isnan(prices.loc[next_date, stock]):
                self.executor.execute_sell(portfolio, stock, prices.loc[next_date, stock], next_date)

        # 平空头
        for stock in portfolio.get_short_stocks_to_cover(bottom_stocks, date, holding_period, all_dates):
            if stock in prices.columns and not np.isnan(prices.loc[next_date, stock]):
                self.executor.execute_cover_short(portfolio, stock, prices.loc[next_date, stock], next_date)

        # 开多头
        long_to_open = portfolio.get_stocks_to_buy(top_stocks)
        if long_to_open:
            capital = portfolio.get_cash() / 2 / len(long_to_open)
            for stock in long_to_open:
                if stock in prices.columns:
                    price = prices.loc[next_date, stock]
                    if not np.isnan(price) and price > 0:
                        self.executor.execute_buy(portfolio, stock, price, capital, next_date)

        # 开空头
        short_to_open = portfolio.get_stocks_to_short(bottom_stocks)
        if short_to_open:
            capital = portfolio.get_cash() / 2 / len(short_to_open)
            for stock in short_to_open:
                if stock in prices.columns:
                    price = prices.loc[next_date, stock]
                    if not np.isnan(price) and price > 0:
                        self.executor.execute_short_sell(
                            portfolio, stock, price, capital, margin_ratio, margin_rate, next_date
                        )

    def _process_chunk(
        self, chunk_dates, chunk_signals, chunk_prices, portfolio, recorder,
        top_n, holding_period, rebalance_dates, actual_start_idx, actual_end_idx, all_dates
    ):
        actual_dates = all_dates[actual_start_idx:actual_end_idx]

        for i, date in enumerate(chunk_dates):
            # 计算净值
            holdings_value = 0.0
            for stock, pos in portfolio.long_positions.items():
                if stock in chunk_prices.columns:
                    try:
                        price = chunk_prices.loc[date, stock]
                        if not np.isnan(price):
                            holdings_value += pos['shares'] * price
                    except KeyError:
                        pass

            # 记录（仅实际窗口）
            if date in actual_dates:
                recorder.record_portfolio_value(
                    date, portfolio.get_cash(), holdings_value, portfolio.get_cash() + holdings_value
                )
                recorder.record_positions(date, portfolio.get_long_only_snapshot())

            # 调仓
            if date in rebalance_dates and date in chunk_signals.index and i < len(chunk_dates) - 1:
                next_date = chunk_dates[i + 1]
                top_stocks = chunk_signals.loc[date].dropna().nlargest(top_n).index.tolist()

                # 卖出
                for stock, pos in list(portfolio.long_positions.items()):
                    try:
                        holding_days = all_dates.index(date) - all_dates.index(pos['entry_date'])
                    except ValueError:
                        holding_days = holding_period

                    if (stock not in top_stocks or holding_days >= holding_period) and stock in chunk_prices.columns:
                        try:
                            price = chunk_prices.loc[next_date, stock]
                            if not np.isnan(price) and price > 0:
                                self.executor.execute_sell(portfolio, stock, price, next_date)
                        except KeyError:
                            pass

                # 买入
                stocks_to_buy = [s for s in top_stocks if s not in portfolio.long_positions]
                if stocks_to_buy:
                    capital = portfolio.get_cash() / len(stocks_to_buy)
                    for stock in stocks_to_buy:
                        if stock in chunk_prices.columns:
                            try:
                                price = chunk_prices.loc[next_date, stock]
                                if not np.isnan(price) and price > 0:
                                    self.executor.execute_buy(portfolio, stock, price, capital, next_date)
                            except KeyError:
                                pass
