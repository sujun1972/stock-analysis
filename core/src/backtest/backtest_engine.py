"""
回测引擎核心模块
实现向量化回测，支持A股T+1交易规则
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any
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

    def backtest_three_layer(
        self,
        selector,
        entry,
        exit_strategy,
        prices: pd.DataFrame,
        start_date: str,
        end_date: str,
        rebalance_freq: str = 'W',
        initial_capital: float = None,
        commission_rate: float = 0.0003,
        slippage_rate: float = 0.0005,
    ) -> Response:
        """
        三层架构回测

        参数:
            selector: 股票选择器 (StockSelector)
            entry: 入场策略 (EntryStrategy)
            exit_strategy: 退出策略 (ExitStrategy)
            prices: 价格数据 DataFrame(index=日期, columns=股票代码)
            start_date: 开始日期
            end_date: 结束日期
            rebalance_freq: 选股频率 ('D'=日, 'W'=周, 'M'=月)
            initial_capital: 初始资金（如果为None则使用self.initial_capital）
            commission_rate: 佣金费率
            slippage_rate: 滑点费率

        返回:
            Response对象，包含:
                - equity_curve: 净值曲线
                - positions: 持仓记录
                - trades: 交易记录
                - metrics: 绩效指标
        """
        from ..strategies.three_layer.base.exit_strategy import Position

        # 使用传入的初始资金或默认值
        capital = initial_capital if initial_capital is not None else self.initial_capital

        logger.info(f"\n开始三层架构回测...")
        logger.info(
            f"初始资金: {capital:,.0f}, "
            f"调仓频率: {rebalance_freq}, "
            f"选股器: {selector.name}, "
            f"入场: {entry.name}, "
            f"退出: {exit_strategy.name}"
        )

        # 1. 初始化
        portfolio = BacktestPortfolio(capital)
        recorder = BacktestRecorder()

        # 2. 过滤日期范围
        dates = pd.date_range(start_date, end_date, freq='D')
        dates = dates.intersection(prices.index)

        if len(dates) == 0:
            logger.error(f"日期范围 {start_date} 到 {end_date} 没有数据")
            return Response.error("日期范围没有数据")

        logger.info(f"回测日期范围: {dates[0]} 到 {dates[-1]} ({len(dates)}天)")

        # 3. 计算调仓日期
        rebalance_dates = set(self._get_rebalance_dates_list(dates, rebalance_freq))
        logger.info(f"调仓次数: {len(rebalance_dates)}")

        # 4. 准备股票数据字典（OHLCV格式）
        stock_data = self._prepare_stock_data_dict(prices)

        # 5. 当前候选股票池
        candidate_stocks = []

        # 6. 主回测循环
        for date in dates:
            if date not in prices.index:
                continue

            logger.debug(f"回测日期: {date}")

            # 6.1 更新持仓价格
            portfolio.update_prices(prices.loc[date])
            recorder.record_equity(date, portfolio.get_total_equity())

            # 记录持仓
            recorder.record_positions(date, portfolio.get_long_only_snapshot())

            # 6.2 Layer 3: 检查退出信号（每日检查）
            if portfolio.long_positions:
                # 构建Position对象字典
                positions_dict = {}
                for stock, pos in portfolio.long_positions.items():
                    positions_dict[stock] = Position(
                        stock_code=stock,
                        entry_date=pos['entry_date'],
                        entry_price=pos['entry_price'],
                        shares=pos['shares'],
                        current_price=pos.get('current_price', pos['entry_price']),
                        unrealized_pnl=pos.get('unrealized_pnl', 0.0),
                        unrealized_pnl_pct=pos.get('unrealized_pnl_pct', 0.0)
                    )

                # 生成退出信号
                exit_signals = exit_strategy.generate_exit_signals(
                    positions_dict, stock_data, date
                )

                # 执行卖出
                for stock in exit_signals:
                    if stock in portfolio.long_positions:
                        sell_price = prices.loc[date, stock] * (1 - slippage_rate)
                        if pd.isna(sell_price) or sell_price <= 0:
                            logger.warning(f"{stock}: 卖出价格无效，跳过")
                            continue

                        shares = portfolio.long_positions[stock]['shares']
                        # 佣金 + 印花税
                        total_commission = commission_rate + 0.001
                        portfolio.sell(stock, shares, sell_price, total_commission)
                        recorder.record_trade(date, stock, 'sell', shares, sell_price)
                        logger.debug(f"卖出 {stock}: {shares} 股 @ {sell_price:.2f}")

            # 6.3 Layer 1: 选股（按调仓频率）
            if date in rebalance_dates:
                candidate_stocks = selector.select(date, prices)
                logger.info(f"调仓日 {date.date()}: 选出 {len(candidate_stocks)} 只候选股票")

            # 6.4 Layer 2: 入场信号（每日检查）
            if candidate_stocks:
                # 过滤掉已持有的股票
                available_candidates = [
                    s for s in candidate_stocks
                    if s not in portfolio.long_positions
                ]

                if available_candidates:
                    entry_signals = entry.generate_entry_signals(
                        available_candidates, stock_data, date
                    )

                    # 执行买入
                    if entry_signals:
                        total_weight = sum(entry_signals.values())
                        if total_weight > 0:
                            for stock, weight in entry_signals.items():
                                normalized_weight = weight / total_weight
                                target_value = portfolio.cash * normalized_weight

                                buy_price = prices.loc[date, stock] * (1 + slippage_rate)
                                if pd.isna(buy_price) or buy_price <= 0:
                                    logger.warning(f"{stock}: 买入价格无效，跳过")
                                    continue

                                shares = int(target_value // (buy_price * (1 + commission_rate)))

                                if shares > 0:
                                    portfolio.buy(stock, shares, buy_price, commission_rate, date)
                                    recorder.record_trade(date, stock, 'buy', shares, buy_price)
                                    logger.debug(f"买入 {stock}: {shares} 股 @ {buy_price:.2f}")

        # 7. 计算绩效指标
        equity_curve = recorder.get_equity_curve()

        if equity_curve.empty:
            logger.error("回测失败：没有生成净值曲线")
            return Response.error("回测失败：没有生成净值曲线")

        metrics = self._calculate_three_layer_metrics(equity_curve, recorder.trades, capital)

        logger.info(f"回测完成: 最终资产 {equity_curve.iloc[-1]:,.0f}")

        return Response.success(
            data={
                'equity_curve': equity_curve,
                'positions': recorder.positions_history,
                'trades': recorder.get_trades_df(),
                'metrics': metrics
            },
            message="三层架构回测完成",
            backtest_type="three_layer",
            n_days=len(equity_curve),
            initial_capital=capital,
            final_value=float(equity_curve.iloc[-1]),
            total_return=float((equity_curve.iloc[-1] / capital - 1))
        )

    # ==================== 私有辅助方法 ====================

    def _get_rebalance_dates(self, dates: pd.DatetimeIndex, freq: str):
        if freq == 'D':
            return dates
        elif freq == 'W':
            return dates[dates.to_series().dt.dayofweek == 0]
        elif freq == 'M':
            return dates[dates.to_series().dt.is_month_start]
        raise ValueError(f"不支持的调仓频率: {freq}")

    def _get_rebalance_dates_list(self, dates: pd.DatetimeIndex, freq: str) -> List[pd.Timestamp]:
        """
        计算调仓日期（用于三层架构回测）

        参数:
            dates: 日期序列
            freq: 调仓频率 ('D'=日, 'W'=周, 'M'=月)

        返回:
            调仓日期列表
        """
        if freq == 'D':
            return dates.tolist()
        elif freq == 'W':
            # 每周一调仓，第一天也调仓
            return [dates[0]] + [d for d in dates if d.dayofweek == 0]
        elif freq == 'M':
            # 每月首日调仓，第一天也调仓
            return [dates[0]] + [d for d in dates if d.day == 1]
        else:
            raise ValueError(f"不支持的调仓频率: {freq}")

    def _prepare_stock_data_dict(self, prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        准备股票数据字典（OHLCV格式，用于三层架构回测）

        注意：如果没有OHLCV数据，使用收盘价模拟

        参数:
            prices: 价格DataFrame (index=日期, columns=股票代码)

        返回:
            股票数据字典 {股票代码: OHLCV DataFrame}
        """
        stock_data = {}

        for stock in prices.columns:
            stock_data[stock] = pd.DataFrame({
                'open': prices[stock],    # 模拟数据
                'high': prices[stock],
                'low': prices[stock],
                'close': prices[stock],
                'volume': 1000000         # 模拟数据
            }, index=prices.index)

        return stock_data

    def _calculate_three_layer_metrics(
        self,
        equity_curve: pd.Series,
        trades: List[Dict],
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        计算三层架构回测的绩效指标

        参数:
            equity_curve: 净值曲线
            trades: 交易记录
            initial_capital: 初始资金

        返回:
            绩效指标字典
        """
        if equity_curve.empty:
            return {}

        # 计算收益率
        daily_returns = equity_curve.pct_change().dropna()

        # 基础指标
        final_value = equity_curve.iloc[-1]
        total_return = (final_value / initial_capital - 1)

        # 年化收益率
        n_days = len(equity_curve)
        n_years = n_days / 252
        if n_years > 0:
            annual_return = (final_value / initial_capital) ** (1 / n_years) - 1
        else:
            annual_return = 0.0

        # 波动率
        if len(daily_returns) > 1:
            volatility = daily_returns.std() * np.sqrt(252)
        else:
            volatility = 0.0

        # 夏普比率
        if volatility > 0:
            sharpe_ratio = annual_return / volatility
        else:
            sharpe_ratio = 0.0

        # 最大回撤
        cumulative_max = equity_curve.cummax()
        drawdown = (equity_curve - cumulative_max) / cumulative_max
        max_drawdown = drawdown.min()

        # 交易统计
        n_trades = len(trades)
        if n_trades > 0:
            buy_trades = [t for t in trades if t['direction'] == 'buy']
            sell_trades = [t for t in trades if t['direction'] == 'sell']
            n_buy = len(buy_trades)
            n_sell = len(sell_trades)
        else:
            n_buy = 0
            n_sell = 0

        metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'n_trades': n_trades,
            'n_buy': n_buy,
            'n_sell': n_sell,
            'n_days': n_days
        }

        return metrics

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
