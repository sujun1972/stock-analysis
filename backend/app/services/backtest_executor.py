"""
回测执行器
负责执行回测逻辑和交易模拟
"""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from loguru import logger

from src.backtest import BacktestEngine, PerformanceAnalyzer
from src.features import AlphaFactors


class BacktestExecutor:
    """
    回测执行器

    职责：
    - 单股回测执行
    - 多股组合回测执行
    - 交易模拟
    - 信号生成
    - 绩效指标计算
    """

    def __init__(self):
        """初始化回测执行器"""
        pass

    def execute_single_stock_backtest(
        self,
        df: pd.DataFrame,
        strategy,
        initial_cash: float,
        benchmark_data: pd.DataFrame = None
    ) -> Dict:
        """
        执行单股回测

        Args:
            df: 股票价格数据
            strategy: 策略实例
            initial_cash: 初始资金
            benchmark_data: 基准数据（可选）

        Returns:
            回测结果字典（包含净值曲线、交易记录、绩效指标）
        """
        logger.info(f"执行单股回测，策略: {strategy.name}")

        # 1. 生成交易信号
        signals = strategy.generate_signals(df)

        # 2. 模拟交易并计算净值
        equity_curve, trades = self.simulate_trades(df, signals, initial_cash)

        # 3. 计算绩效指标
        metrics = self.calculate_metrics(equity_curve, benchmark_data)

        return {
            'equity_curve': equity_curve,
            'trades': trades,
            'metrics': metrics
        }

    def execute_multi_stock_backtest(
        self,
        prices_dict: Dict[str, pd.DataFrame],
        strategy,
        initial_cash: float,
        benchmark_data: pd.DataFrame = None
    ) -> Dict:
        """
        执行多股组合回测

        Args:
            prices_dict: 股票代码 -> DataFrame 字典
            strategy: 策略实例
            initial_cash: 初始资金
            benchmark_data: 基准数据（可选）

        Returns:
            回测结果字典（包含组合净值、持仓、绩效指标）
        """
        logger.info(f"执行多股组合回测，股票数量: {len(prices_dict)}，策略: {strategy.name}")

        # 1. 构建价格矩阵
        prices_df = pd.DataFrame({
            symbol: df['close'] for symbol, df in prices_dict.items()
        })

        # 2. 生成Alpha因子信号
        signals_df = self.generate_alpha_signals(prices_dict)

        # 3. 运行回测引擎
        strategy_params = strategy.params if hasattr(strategy, 'params') else {}
        engine = BacktestEngine(
            initial_capital=initial_cash,
            verbose=False
        )

        results = engine.backtest_long_only(
            signals=signals_df,
            prices=prices_df,
            top_n=strategy_params.get('top_n', 10),
            holding_period=strategy_params.get('holding_period', 5),
            rebalance_freq=strategy_params.get('rebalance_freq', 'W')
        )

        # 4. 计算绩效指标
        analyzer = PerformanceAnalyzer(results['daily_returns'])
        if benchmark_data is not None and len(benchmark_data) > 0:
            analyzer.set_benchmark(benchmark_data['returns'])

        metrics = {
            'total_return': analyzer.total_return(),
            'annualized_return': analyzer.annualized_return(),
            'sharpe_ratio': analyzer.sharpe_ratio(),
            'max_drawdown': analyzer.max_drawdown(),
            'max_drawdown_duration': analyzer.max_drawdown_duration(),
            'volatility': analyzer.volatility(),
            'calmar_ratio': analyzer.calmar_ratio(),
            'sortino_ratio': analyzer.sortino_ratio(),
            'alpha': analyzer.alpha() if benchmark_data is not None else None,
            'beta': analyzer.beta() if benchmark_data is not None else None,
            'information_ratio': analyzer.information_ratio() if benchmark_data is not None else None
        }

        return {
            'portfolio_value': results['portfolio_value'],
            'positions': results['positions'],
            'daily_returns': results['daily_returns'],
            'metrics': metrics
        }

    def simulate_trades(
        self,
        df: pd.DataFrame,
        signals: pd.Series,
        initial_cash: float
    ) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        模拟交易执行

        Args:
            df: 价格数据
            signals: 交易信号（1=买入, -1=卖出, 0=持有）
            initial_cash: 初始资金

        Returns:
            (净值曲线DataFrame, 交易记录列表)
        """
        cash = initial_cash
        shares = 0
        equity = []
        trades = []

        for date, signal in signals.items():
            if date not in df.index:
                continue

            price = df.loc[date, 'close']

            # 买入信号
            if signal == 1 and shares == 0:
                shares = int(cash / price / 100) * 100  # A股100股为1手
                if shares >= 100:
                    cost = shares * price * 1.0003  # 佣金
                    cash -= cost
                    trades.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'type': 'buy',
                        'price': float(price),
                        'shares': int(shares),
                        'amount': float(cost)
                    })

            # 卖出信号
            elif signal == -1 and shares > 0:
                proceeds = shares * price * 0.9987  # 佣金+印花税
                cash += proceeds
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'type': 'sell',
                    'price': float(price),
                    'shares': int(shares),
                    'amount': float(proceeds)
                })
                shares = 0

            # 记录每日净值
            market_value = shares * price
            total_value = cash + market_value
            equity.append({
                'date': date,
                'total': total_value,
                'cash': cash,
                'holdings': market_value
            })

        equity_df = pd.DataFrame(equity).set_index('date')
        equity_df['returns'] = equity_df['total'].pct_change()

        return equity_df, trades

    def generate_alpha_signals(
        self,
        prices_dict: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        生成Alpha因子信号矩阵

        Args:
            prices_dict: 股票代码 -> DataFrame 字典

        Returns:
            信号DataFrame
        """
        signals_dict = {}
        alpha = AlphaFactors()

        for symbol, df in prices_dict.items():
            try:
                # 计算多个Alpha因子
                momentum = alpha.calculate_momentum(df['close'], period=20)
                mean_reversion = alpha.calculate_mean_reversion(df['close'], period=10)

                # 综合信号(简单平均)
                signal = (momentum + mean_reversion) / 2
                signals_dict[symbol] = signal
            except Exception as e:
                logger.error(f"计算 {symbol} Alpha因子失败: {e}")

        return pd.DataFrame(signals_dict)

    def calculate_metrics(
        self,
        equity_curve: pd.DataFrame,
        benchmark_data: pd.DataFrame = None
    ) -> Dict:
        """
        计算绩效指标

        Args:
            equity_curve: 净值曲线
            benchmark_data: 基准数据（可选）

        Returns:
            绩效指标字典
        """
        analyzer = PerformanceAnalyzer(equity_curve['returns'])

        if benchmark_data is not None and len(benchmark_data) > 0:
            analyzer.set_benchmark(benchmark_data['returns'])

        # 计算交易胜率
        win_rate = 0.0
        if 'trades' in equity_curve.columns:
            trades = equity_curve['trades'].dropna()
            if len(trades) > 0:
                win_rate = analyzer.win_rate()

        metrics = {
            'total_return': analyzer.total_return(),
            'annualized_return': analyzer.annualized_return(),
            'sharpe_ratio': analyzer.sharpe_ratio(),
            'max_drawdown': analyzer.max_drawdown(),
            'max_drawdown_duration': analyzer.max_drawdown_duration(),
            'volatility': analyzer.volatility(),
            'win_rate': win_rate,
            'calmar_ratio': analyzer.calmar_ratio(),
            'sortino_ratio': analyzer.sortino_ratio()
        }

        return metrics
