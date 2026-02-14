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
        rebalance_freq: str = 'W',
        exit_manager=None
    ) -> Response:
        """
        纯多头回测（等权重选股策略）

        参数:
            exit_manager: 离场管理器（可选），如果提供则会在每日检查离场信号
        """
        logger.info(f"\n开始回测...")
        logger.info(f"初始资金: {self.initial_capital:,.0f}, 选股: {top_n}只, 调仓: {rebalance_freq}")
        if exit_manager:
            logger.info(f"已启用离场策略管理器")

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

            # 检查离场信号（每日检查）
            if exit_manager and i < len(dates) - 1:
                next_date = dates[i + 1]
                current_positions = self._prepare_positions_for_exit_check(portfolio, prices, date)

                if current_positions:
                    # 准备入场信号（用于反向离场检测）
                    entry_signals = {}
                    if date in signals.index:
                        top_signals = signals.loc[date].nlargest(top_n)
                        for stock_code, signal_value in top_signals.items():
                            if signal_value > 0:
                                # 格式化为符合 exit_manager 期望的格式
                                entry_signals[stock_code] = {
                                    'action': 'long',  # 默认为多头信号
                                    'weight': float(signal_value)
                                }

                    # 检查离场信号
                    exit_signals = exit_manager.check_exit(
                        positions=current_positions,
                        current_prices={stock: prices.loc[date, stock] for stock in prices.columns if stock in prices.loc[date]},
                        current_date=date,
                        entry_signals=entry_signals,
                        market_data=None
                    )

                    # 执行离场
                    for stock_code, exit_signal in exit_signals.items():
                        if stock_code in portfolio.long_positions:
                            position = portfolio.long_positions[stock_code]
                            qty = position['shares']
                            exit_price = prices.loc[next_date, stock_code] if stock_code in prices.columns else None
                            if exit_price and pd.notna(exit_price):
                                # 计算总佣金率（包含印花税）
                                total_commission_rate = self.commission_rate + self.stamp_tax_rate

                                # 执行卖出
                                portfolio.sell(
                                    stock_code=stock_code,
                                    shares=qty,
                                    price=exit_price,
                                    commission_rate=total_commission_rate
                                )

                                # 计算交易后的资产状态
                                cash_after = portfolio.get_cash()
                                holdings_value = portfolio.calculate_long_holdings_value(prices, next_date)
                                total_value = cash_after + holdings_value

                                # 记录交易（包含离场原因和资产状态）
                                recorder.record_trade(
                                    date=next_date,
                                    stock_code=stock_code,
                                    direction='sell',
                                    shares=qty,
                                    price=exit_price,
                                    exit_reason=exit_signal.reason,
                                    exit_trigger=exit_signal.trigger,
                                    cash_after=cash_after,
                                    holdings_value_after=holdings_value,
                                    total_value_after=total_value
                                )
                                logger.info(f"  [{date}] 离场 {stock_code}: {exit_signal.trigger} (原因: {exit_signal.reason})")

            # 调仓
            if date in rebalance_dates and i < len(dates) - 1:
                self._rebalance_long_only(
                    portfolio, signals, prices, date, dates[i + 1], top_n, holding_period, dates, recorder
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
                'cost_analyzer': self.cost_analyzer,
                'recorder': recorder  # 添加 recorder 以获取交易记录
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

    def backtest_ml_strategy(
        self,
        ml_entry,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        start_date: str,
        end_date: str,
        rebalance_freq: str = 'W',
        initial_capital: float = None,
        exit_manager = None
    ) -> Response:
        """
        ML策略回测（支持离场策略）

        参数:
            ml_entry: ML入场策略实例 (MLEntry)
            stock_pool: 股票池 (可交易股票列表)
            market_data: 市场数据 DataFrame，需包含以下列:
                - date: 日期
                - stock_code: 股票代码
                - open, high, low, close, volume: OHLCV数据
            start_date: 开始日期 (格式: 'YYYY-MM-DD')
            end_date: 结束日期 (格式: 'YYYY-MM-DD')
            rebalance_freq: 调仓频率 ('D'=日, 'W'=周, 'M'=月)
            initial_capital: 初始资金 (如果为None则使用self.initial_capital)
            exit_manager: 离场管理器 (CompositeExitManager，可选)

        返回:
            Response对象，包含:
                - portfolio_value: 净值曲线
                - positions: 持仓记录
                - daily_returns: 每日收益率
                - cost_analysis: 成本分析
                - metrics: 绩效指标
        """
        # 使用传入的初始资金或默认值
        capital = initial_capital if initial_capital is not None else self.initial_capital

        logger.info(f"\n开始ML策略回测...")
        logger.info(
            f"初始资金: {capital:,.0f}, "
            f"调仓频率: {rebalance_freq}, "
            f"股票池: {len(stock_pool)}只, "
            f"离场策略: {'启用' if exit_manager else '禁用'}"
        )

        # 1. 初始化
        portfolio = BacktestPortfolio(capital)
        recorder = BacktestRecorder()

        # 2. 过滤日期范围
        dates = pd.date_range(start_date, end_date, freq='D')
        market_data = market_data.copy()
        market_data['date'] = pd.to_datetime(market_data['date'])

        # 获取实际交易日
        trading_dates = sorted(market_data['date'].unique())
        trading_dates = [d for d in trading_dates if start_date <= d.strftime('%Y-%m-%d') <= end_date]

        if len(trading_dates) == 0:
            logger.error(f"日期范围 {start_date} 到 {end_date} 没有数据")
            return Response.error("日期范围没有数据")

        logger.info(f"回测日期范围: {trading_dates[0].date()} 到 {trading_dates[-1].date()} ({len(trading_dates)}天)")

        # 3. 计算调仓日期（仅用于入场信号生成）
        rebalance_dates = set(self._get_rebalance_dates_list(
            pd.DatetimeIndex(trading_dates), rebalance_freq
        ))
        logger.info(f"调仓次数: {len(rebalance_dates)}")

        # 4. 准备价格数据 (用于计算持仓价值)
        price_pivot = market_data.pivot_table(
            index='date', columns='stock_code', values='close'
        )

        # 5. 统计数据
        exit_stats = {'strategy': 0, 'reverse_entry': 0, 'risk_control': 0}

        # 6. 主回测循环
        for i, date in enumerate(trading_dates):
            date_str = date.strftime('%Y-%m-%d')

            logger.debug(f"回测日期: {date_str}")

            # 6.1 更新持仓价格
            if date in price_pivot.index:
                portfolio.update_prices(price_pivot.loc[date])

            # 记录净值
            value_metrics = portfolio.get_total_value(price_pivot, date)
            recorder.record_market_neutral_value(
                date, value_metrics['cash'], value_metrics['long_value'],
                value_metrics['short_value'], value_metrics['short_pnl'],
                value_metrics['short_interest'], value_metrics['total']
            )
            recorder.record_positions(date, portfolio.get_positions_snapshot())

            # 6.2 生成入场信号（在调仓日）
            entry_signals = None
            if date in rebalance_dates:
                try:
                    entry_signals = ml_entry.generate_signals(
                        stock_pool=stock_pool,
                        market_data=market_data,
                        date=date_str
                    )
                    logger.debug(f"调仓日 {date_str}: 生成 {len(entry_signals)} 个入场信号")
                except Exception as e:
                    logger.warning(f"调仓日 {date_str} 信号生成失败: {e}")
                    entry_signals = {}

            # 6.3 检查离场信号（每日检查）
            if exit_manager and i < len(trading_dates) - 1:
                next_date = trading_dates[i + 1]

                # 准备当前持仓信息
                current_positions = self._prepare_positions_for_exit_check(
                    portfolio, price_pivot, date
                )

                # 准备当前价格字典
                current_prices = {}
                if date in price_pivot.index:
                    current_prices = price_pivot.loc[date].to_dict()

                # 检查离场
                exit_signals = exit_manager.check_exit(
                    positions=current_positions,
                    current_prices=current_prices,
                    current_date=date,
                    entry_signals=entry_signals,
                    market_data=market_data
                )

                # 执行离场
                for stock, exit_signal in exit_signals.items():
                    if stock in price_pivot.columns and next_date in price_pivot.index:
                        sell_price = price_pivot.loc[next_date, stock]
                        if not np.isnan(sell_price) and sell_price > 0:
                            # 多头平仓
                            if stock in portfolio.long_positions:
                                self.executor.execute_sell(portfolio, stock, sell_price, next_date)
                                exit_manager.on_position_closed(stock)
                                exit_stats[exit_signal.reason] += 1
                                logger.debug(
                                    f"离场 {stock} @ {sell_price:.2f}: "
                                    f"{exit_signal.trigger} (原因={exit_signal.reason})"
                                )

                            # 空头平仓
                            elif stock in portfolio.short_positions:
                                self.executor.execute_cover_short(portfolio, stock, sell_price, next_date)
                                exit_manager.on_position_closed(stock)
                                exit_stats[exit_signal.reason] += 1
                                logger.debug(
                                    f"平空 {stock} @ {sell_price:.2f}: "
                                    f"{exit_signal.trigger} (原因={exit_signal.reason})"
                                )

            # 6.4 执行入场（在调仓日，且有入场信号）
            if entry_signals and i < len(trading_dates) - 1:
                next_date = trading_dates[i + 1]
                self._execute_ml_entry(
                    portfolio, entry_signals, price_pivot, date, next_date
                )

        # 7. 保存结果
        self.portfolio_value = recorder.get_portfolio_value_df()
        self.positions = recorder.get_positions_history()
        self.daily_returns = recorder.calculate_daily_returns()

        logger.info(f"回测完成: 最终资产 {self.portfolio_value['total'].iloc[-1]:,.0f}")

        # 输出离场统计
        if exit_manager:
            logger.info(
                f"离场统计: 策略={exit_stats['strategy']}, "
                f"反向入场={exit_stats['reverse_entry']}, "
                f"风控={exit_stats['risk_control']}"
            )

        # 8. 成本分析
        cost_metrics = self.cost_analyzer.analyze_all(
            portfolio_returns=self.daily_returns,
            portfolio_values=self.portfolio_value['total'],
            verbose=False
        )

        # 9. 计算绩效指标
        metrics = self._calculate_ml_strategy_metrics(
            self.portfolio_value['total'],
            self.daily_returns,
            capital
        )

        # 添加离场统计到metrics
        if exit_manager:
            metrics['exit_stats'] = exit_stats

        return Response.success(
            data={
                'portfolio_value': self.portfolio_value,
                'positions': self.positions,
                'daily_returns': self.daily_returns,
                'cost_analysis': cost_metrics,
                'cost_analyzer': self.cost_analyzer,
                'metrics': metrics
            },
            message="ML策略回测完成",
            backtest_type="ml_strategy",
            n_days=len(self.portfolio_value),
            initial_capital=capital,
            final_value=float(self.portfolio_value['total'].iloc[-1]),
            total_return=float((self.portfolio_value['total'].iloc[-1] / capital - 1))
        )

    def _prepare_positions_for_exit_check(
        self,
        portfolio: BacktestPortfolio,
        price_pivot: pd.DataFrame,
        current_date: pd.Timestamp
    ) -> Dict[str, Dict]:
        """
        准备持仓信息用于离场检查

        参数:
            portfolio: 组合对象
            price_pivot: 价格数据
            current_date: 当前日期

        返回:
            持仓信息字典
        """
        positions = {}

        # 多头持仓
        for stock, pos in portfolio.long_positions.items():
            current_price = None
            if stock in price_pivot.columns and current_date in price_pivot.index:
                current_price = price_pivot.loc[current_date, stock]
                if np.isnan(current_price):
                    current_price = pos.get('entry_price', 0)

            if current_price is None or current_price <= 0:
                continue

            entry_price = pos.get('entry_price', current_price)
            unrealized_pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0.0

            positions[stock] = {
                'stock_code': stock,
                'shares': pos.get('shares', 0),
                'entry_price': entry_price,
                'entry_date': pos.get('entry_date', current_date),
                'current_price': current_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'position_type': 'long'
            }

        # 空头持仓
        for stock, pos in portfolio.short_positions.items():
            current_price = None
            if stock in price_pivot.columns and current_date in price_pivot.index:
                current_price = price_pivot.loc[current_date, stock]
                if np.isnan(current_price):
                    current_price = pos.get('entry_price', 0)

            if current_price is None or current_price <= 0:
                continue

            entry_price = pos.get('entry_price', current_price)
            # 空头的盈亏是反向的
            unrealized_pnl_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0.0

            positions[stock] = {
                'stock_code': stock,
                'shares': pos.get('shares', 0),
                'entry_price': entry_price,
                'entry_date': pos.get('entry_date', current_date),
                'current_price': current_price,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'position_type': 'short'
            }

        return positions

    def _execute_ml_entry(
        self,
        portfolio: BacktestPortfolio,
        signals: Dict[str, Dict],
        price_pivot: pd.DataFrame,
        current_date: pd.Timestamp,
        next_date: pd.Timestamp
    ):
        """
        执行ML入场信号（不自动平仓已有持仓）

        与 _execute_ml_rebalance 的区别：
        - _execute_ml_rebalance: 调仓式，平掉不在信号中的持仓
        - _execute_ml_entry: 只执行新入场，保留现有持仓（离场由exit_manager处理）

        参数:
            portfolio: 组合对象
            signals: ML信号字典 {stock: {'action': 'long'/'short', 'weight': 0.xx}}
            price_pivot: 价格数据 (date × stock_code)
            current_date: 当前日期
            next_date: 下一交易日 (执行价格)
        """
        if not signals:
            return

        # 分离做多和做空信号
        long_signals = {s: v for s, v in signals.items() if v['action'] == 'long'}
        short_signals = {s: v for s, v in signals.items() if v['action'] == 'short'}

        # 计算可用资金
        total_equity = portfolio.get_total_value(price_pivot, current_date)['total']
        available_cash = total_equity

        # 开多头 / 调整多头仓位
        for stock, signal in long_signals.items():
            if stock not in price_pivot.columns or next_date not in price_pivot.index:
                continue

            buy_price = price_pivot.loc[next_date, stock]
            if np.isnan(buy_price) or buy_price <= 0:
                continue

            target_value = available_cash * signal['weight']

            # 如果已持有，先卖出
            if stock in portfolio.long_positions:
                self.executor.execute_sell(portfolio, stock, buy_price, next_date)

            # 买入
            if target_value > 0:
                self.executor.execute_buy(portfolio, stock, buy_price, target_value, next_date)
                logger.debug(f"入场多头: {stock} @ {buy_price:.2f}, 权重: {signal['weight']:.3f}")

        # 开空头 / 调整空头仓位
        for stock, signal in short_signals.items():
            if stock not in price_pivot.columns or next_date not in price_pivot.index:
                continue

            short_price = price_pivot.loc[next_date, stock]
            if np.isnan(short_price) or short_price <= 0:
                continue

            target_value = available_cash * signal['weight']

            # 如果已持有，先平仓
            if stock in portfolio.short_positions:
                self.executor.execute_cover_short(portfolio, stock, short_price, next_date)

            # 开空
            if target_value > 0:
                margin_ratio = 0.5  # 50%保证金
                margin_rate = 0.10  # 10%融券费率
                self.executor.execute_short_sell(
                    portfolio, stock, short_price, target_value,
                    margin_ratio, margin_rate, next_date
                )
                logger.debug(f"入场空头: {stock} @ {short_price:.2f}, 权重: {signal['weight']:.3f}")


    # ==================== 私有辅助方法 ====================

    def _execute_ml_rebalance(
        self,
        portfolio: BacktestPortfolio,
        signals: Dict[str, Dict],
        price_pivot: pd.DataFrame,
        current_date: pd.Timestamp,
        next_date: pd.Timestamp
    ):
        """
        执行ML策略调仓

        参数:
            portfolio: 组合对象
            signals: ML信号字典 {stock: {'action': 'long'/'short', 'weight': 0.xx}}
            price_pivot: 价格数据 (date × stock_code)
            current_date: 当前日期
            next_date: 下一交易日 (执行价格)
        """
        if not signals:
            return

        # 1. 分离做多和做空信号
        long_signals = {s: v for s, v in signals.items() if v['action'] == 'long'}
        short_signals = {s: v for s, v in signals.items() if v['action'] == 'short'}

        # 2. 平掉不在信号中的多头持仓
        current_long_stocks = list(portfolio.long_positions.keys())
        target_long_stocks = list(long_signals.keys())

        for stock in current_long_stocks:
            if stock not in target_long_stocks:
                if stock in price_pivot.columns and next_date in price_pivot.index:
                    sell_price = price_pivot.loc[next_date, stock]
                    if not np.isnan(sell_price) and sell_price > 0:
                        self.executor.execute_sell(portfolio, stock, sell_price, next_date)
                        logger.debug(f"平多头: {stock} @ {sell_price:.2f}")

        # 3. 平掉不在信号中的空头持仓
        current_short_stocks = list(portfolio.short_positions.keys())
        target_short_stocks = list(short_signals.keys())

        for stock in current_short_stocks:
            if stock not in target_short_stocks:
                if stock in price_pivot.columns and next_date in price_pivot.index:
                    cover_price = price_pivot.loc[next_date, stock]
                    if not np.isnan(cover_price) and cover_price > 0:
                        self.executor.execute_cover_short(portfolio, stock, cover_price, next_date)
                        logger.debug(f"平空头: {stock} @ {cover_price:.2f}")

        # 4. 计算可用资金 (扣除空头保证金)
        total_equity = portfolio.get_total_value(price_pivot, current_date)['total']
        available_cash = total_equity

        # 5. 开多头 / 调整多头仓位
        for stock, signal in long_signals.items():
            if stock not in price_pivot.columns or next_date not in price_pivot.index:
                continue

            buy_price = price_pivot.loc[next_date, stock]
            if np.isnan(buy_price) or buy_price <= 0:
                continue

            target_value = available_cash * signal['weight']

            # 如果已持有，先卖出
            if stock in portfolio.long_positions:
                self.executor.execute_sell(portfolio, stock, buy_price, next_date)

            # 买入
            if target_value > 0:
                self.executor.execute_buy(portfolio, stock, buy_price, target_value, next_date)
                logger.debug(f"开多头: {stock} @ {buy_price:.2f}, 权重: {signal['weight']:.3f}")

        # 6. 开空头 / 调整空头仓位
        for stock, signal in short_signals.items():
            if stock not in price_pivot.columns or next_date not in price_pivot.index:
                continue

            short_price = price_pivot.loc[next_date, stock]
            if np.isnan(short_price) or short_price <= 0:
                continue

            target_value = available_cash * signal['weight']

            # 如果已持有，先平仓
            if stock in portfolio.short_positions:
                self.executor.execute_cover_short(portfolio, stock, short_price, next_date)

            # 开空
            if target_value > 0:
                margin_ratio = 0.5  # 50%保证金
                margin_rate = 0.10  # 10%融券费率
                self.executor.execute_short_sell(
                    portfolio, stock, short_price, target_value,
                    margin_ratio, margin_rate, next_date
                )
                logger.debug(f"开空头: {stock} @ {short_price:.2f}, 权重: {signal['weight']:.3f}")

    def _calculate_ml_strategy_metrics(
        self,
        equity_curve: pd.Series,
        daily_returns: pd.Series,
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        计算ML策略回测的绩效指标

        参数:
            equity_curve: 净值曲线
            daily_returns: 每日收益率
            initial_capital: 初始资金

        返回:
            绩效指标字典
        """
        if equity_curve.empty:
            return {}

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

        # 胜率
        if len(daily_returns) > 0:
            win_rate = (daily_returns > 0).sum() / len(daily_returns)
        else:
            win_rate = 0.0

        metrics = {
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'n_days': n_days
        }

        return metrics

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


    def _rebalance_long_only(
        self, portfolio, signals, prices, date, next_date, top_n, holding_period, all_dates, recorder=None
    ):
        """
        调仓逻辑（优化版）：只负责买入新股票，卖出由离场策略管理

        设计理念：
        - 调仓日：根据信号强度选出top_n股票，买入尚未持有的股票
        - 离场决策：完全由exit_manager管理（止盈、止损、持仓时长等）
        - 避免问题：不再出现"同价卖出再买入"的无效交易

        参数:
            portfolio: 投资组合
            signals: 信号DataFrame
            prices: 价格DataFrame
            date: 当前日期
            next_date: 下一交易日
            top_n: 选股数量
            holding_period: 持仓期限（该参数已废弃，保留仅为向后兼容）
            all_dates: 所有交易日期
            recorder: 交易记录器
        """
        # 选股：根据信号强度选出top_n
        date_signals = signals.loc[date].dropna()

        # 防御性编程：确保数据类型正确（避免object类型导致nlargest失败）
        if date_signals.dtype == 'object':
            date_signals = pd.to_numeric(date_signals, errors='coerce').dropna()

        top_stocks = date_signals.nlargest(top_n).index.tolist()

        # ========== 移除自动卖出逻辑 ==========
        # 原逻辑：卖出不在top_n中的股票 OR 持仓超过holding_period的股票
        # 新逻辑：卖出决策完全由exit_manager在每日检查中处理
        # 优势：
        #   1. 避免盈利股票因持仓到期被强制卖出
        #   2. 避免同价卖出再买入的无效交易
        #   3. 离场原因更准确（止盈/止损/信号反转，而非统一标记为"调仓"）

        # 买入新股票（仅买入尚未持有的股票）
        stocks_to_buy = portfolio.get_stocks_to_buy(top_stocks)
        if stocks_to_buy:
            capital_per_stock = portfolio.get_cash() / len(stocks_to_buy)
            for stock in stocks_to_buy:
                if stock in prices.columns:
                    buy_price = prices.loc[next_date, stock]
                    if not np.isnan(buy_price) and buy_price > 0:
                        # 计算可买数量（A股最小交易单位100股）
                        shares = int(capital_per_stock / buy_price / 100) * 100
                        if shares > 0:
                            # 执行买入
                            success = portfolio.buy(
                                stock_code=stock,
                                shares=shares,
                                price=buy_price,
                                commission_rate=self.commission_rate,
                                date=next_date
                            )

                            # 记录交易（买入成功时）
                            if success and recorder:
                                # 计算交易后资产状态
                                cash_after = portfolio.get_cash()
                                holdings_value = portfolio.calculate_long_holdings_value(prices, next_date)
                                total_value = cash_after + holdings_value

                                # 记录交易：entry_reason改为'signal'（信号触发）
                                recorder.record_trade(
                                    date=next_date,
                                    stock_code=stock,
                                    direction='buy',
                                    shares=shares,
                                    price=buy_price,
                                    entry_reason='signal',  # 修改：更准确的入场原因
                                    cash_after=cash_after,
                                    holdings_value_after=holdings_value,
                                    total_value_after=total_value
                                )

    def _rebalance_market_neutral(
        self, portfolio, signals, prices, date, next_date,
        top_n, bottom_n, holding_period, all_dates, margin_rate, margin_ratio
    ):
        # 选股
        today_signals = signals.loc[date].dropna()

        # 防御性编程：确保数据类型正确（避免object类型导致nlargest/nsmallest失败）
        if today_signals.dtype == 'object':
            today_signals = pd.to_numeric(today_signals, errors='coerce').dropna()

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
                date_chunk_signals = chunk_signals.loc[date].dropna()

                # 防御性编程：确保数据类型正确
                if date_chunk_signals.dtype == 'object':
                    date_chunk_signals = pd.to_numeric(date_chunk_signals, errors='coerce').dropna()

                top_stocks = date_chunk_signals.nlargest(top_n).index.tolist()

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
