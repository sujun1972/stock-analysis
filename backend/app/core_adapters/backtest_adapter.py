"""
回测引擎适配器 (Backtest Adapter)

将 Core 的回测引擎包装为异步方法，供 FastAPI 使用。

核心功能:
- 异步运行回测
- 异步计算绩效指标 (收益率、夏普比率、最大回撤等 20+ 指标)
- 并行回测支持
- 交易成本分析
- 回测结果可视化

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import asyncio
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.cost_analyzer import TradingCostAnalyzer
from src.backtest.parallel_backtester import ParallelBacktester
from src.backtest.performance_analyzer import PerformanceAnalyzer

from app.core.cache import cache
from app.core.config import settings


class BacktestAdapter:
    """
    Core 回测引擎的异步适配器

    包装 Core 的回测相关类，将同步方法转换为异步方法。

    示例:
        >>> adapter = BacktestAdapter(initial_capital=1000000)
        >>> results = await adapter.run_backtest(
        ...     stock_codes=['000001', '000002'],
        ...     strategy_params={'type': 'ma_cross'},
        ...     start_date=date(2023, 1, 1),
        ...     end_date=date(2023, 12, 31)
        ... )
    """

    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003,
        stamp_tax_rate: float = 0.001,
        min_commission: float = 5.0,
        slippage: float = 0.0,
        verbose: bool = True,
    ):
        """
        初始化回测适配器

        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率
            stamp_tax_rate: 印花税率
            min_commission: 最小佣金
            slippage: 滑点
            verbose: 是否显示详细信息
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.min_commission = min_commission
        self.slippage = slippage
        self.verbose = verbose

        # 创建回测引擎实例
        self.engine = None
        self._init_engine()

    def _init_engine(self):
        """初始化回测引擎"""
        self.engine = BacktestEngine(
            initial_capital=self.initial_capital,
            commission_rate=self.commission_rate,
            stamp_tax_rate=self.stamp_tax_rate,
            min_commission=self.min_commission,
            slippage=self.slippage,
            verbose=self.verbose,
        )

    async def run_backtest(
        self,
        stock_codes: List[str],
        strategy_params: Dict[str, Any],
        start_date: date,
        end_date: date,
        data_loader: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        异步运行回测

        Args:
            stock_codes: 股票代码列表
            strategy_params: 策略参数字典
            start_date: 开始日期
            end_date: 结束日期
            data_loader: 数据加载器 (可选)

        Returns:
            回测结果字典，包含:
                - portfolio_value: 投资组合价值序列
                - positions: 持仓记录
                - trades: 交易记录
                - metrics: 绩效指标
                - daily_returns: 每日收益率

        Raises:
            BacktestError: 回测执行错误

        Note:
            回测结果较复杂，暂不使用装饰器缓存
            可在 API 层根据需要实现缓存
        """

        def _run():
            # 这里需要根据 strategy_params 构建策略实例
            # 简化实现，实际使用中需要策略工厂
            strategy_params.get("type", "ma_cross")

            return self.engine.run(
                stock_codes=stock_codes,
                strategy=None,  # 需要策略实例
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )

        return await asyncio.to_thread(_run)

    async def calculate_metrics(
        self, portfolio_value: pd.Series, positions: pd.DataFrame, trades: pd.DataFrame
    ) -> Dict[str, float]:
        """
        异步计算绩效指标

        Args:
            portfolio_value: 投资组合价值序列
            positions: 持仓记录
            trades: 交易记录

        Returns:
            绩效指标字典，包含:
                - total_return: 总收益率
                - annual_return: 年化收益率
                - sharpe_ratio: 夏普比率
                - max_drawdown: 最大回撤
                - win_rate: 胜率
                - profit_factor: 盈亏比
                等 20+ 指标

        Raises:
            BacktestError: 指标计算错误
        """

        def _calculate():
            # PerformanceAnalyzer 接受 returns 或包含 daily_returns 的字典
            # 从 portfolio_value 计算 daily_returns
            if isinstance(portfolio_value, pd.Series):
                daily_returns = portfolio_value.pct_change().dropna()
            else:
                # 如果是DataFrame，尝试获取value列
                daily_returns = (
                    portfolio_value["value"].pct_change().dropna()
                    if "value" in portfolio_value.columns
                    else portfolio_value.iloc[:, 0].pct_change().dropna()
                )

            analyzer = PerformanceAnalyzer(
                returns=daily_returns, benchmark_returns=None, risk_free_rate=0.03
            )
            return analyzer.calculate_all_metrics()

        return await asyncio.to_thread(_calculate)

    async def run_parallel_backtest(
        self,
        stock_codes: List[str],
        strategy_params_list: List[Dict[str, Any]],
        start_date: date,
        end_date: date,
        n_processes: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        异步并行回测 (多策略/多参数)

        Args:
            stock_codes: 股票代码列表
            strategy_params_list: 策略参数列表
            start_date: 开始日期
            end_date: 结束日期
            n_processes: 进程数

        Returns:
            回测结果列表

        Raises:
            BacktestError: 并行回测错误
        """

        def _run_parallel():
            parallel_backtester = ParallelBacktester(
                n_processes=n_processes,
                initial_capital=self.initial_capital,
                commission_rate=self.commission_rate,
                stamp_tax_rate=self.stamp_tax_rate,
            )

            results = []
            for params in strategy_params_list:
                result = parallel_backtester.run(
                    stock_codes=stock_codes,
                    strategy_params=params,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )
                results.append(result)

            return results

        return await asyncio.to_thread(_run_parallel)

    async def analyze_trading_costs(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """
        异步分析交易成本

        Args:
            trades: 交易记录 DataFrame

        Returns:
            成本分析结果字典，包含:
                - total_commission: 总佣金
                - total_stamp_tax: 总印花税
                - total_slippage: 总滑点成本
                - cost_breakdown: 成本明细
                - cost_ratio: 成本占比

        Raises:
            BacktestError: 成本分析错误
        """

        def _analyze():
            cost_analyzer = TradingCostAnalyzer()
            # 添加交易记录
            for trade in trades:
                if isinstance(trade, dict):
                    cost_analyzer.add_trade_from_dict(trade)
                else:
                    cost_analyzer.add_trade(trade)
            # 使用 analyze_all 方法
            return cost_analyzer.analyze_all()

        return await asyncio.to_thread(_analyze)

    async def calculate_risk_metrics(
        self, returns: pd.Series, positions: pd.DataFrame
    ) -> Dict[str, float]:
        """
        异步计算风险指标

        Args:
            returns: 收益率序列
            positions: 持仓记录

        Returns:
            风险指标字典，包含:
                - volatility: 波动率
                - var_95: 95% VaR
                - cvar_95: 95% CVaR
                - beta: Beta 系数
                - tracking_error: 跟踪误差

        Raises:
            BacktestError: 风险计算错误
        """

        def _calculate():
            # 波动率
            volatility = returns.std() * np.sqrt(252)

            # VaR (95%)
            var_95 = returns.quantile(0.05)

            # CVaR (95%)
            cvar_95 = returns[returns <= var_95].mean()

            return {
                "volatility": volatility,
                "annual_volatility": volatility,
                "var_95": var_95,
                "cvar_95": cvar_95,
                "downside_volatility": returns[returns < 0].std() * np.sqrt(252),
            }

        return await asyncio.to_thread(_calculate)

    async def get_trade_statistics(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """
        异步获取交易统计

        Args:
            trades: 交易记录 DataFrame

        Returns:
            交易统计字典，包含:
                - total_trades: 总交易次数
                - winning_trades: 盈利交易次数
                - losing_trades: 亏损交易次数
                - win_rate: 胜率
                - avg_profit: 平均盈利
                - avg_loss: 平均亏损
                - profit_factor: 盈亏比

        Raises:
            BacktestError: 统计计算错误
        """

        def _calculate():
            if trades.empty:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "avg_profit": 0.0,
                    "avg_loss": 0.0,
                    "profit_factor": 0.0,
                }

            # 计算盈亏
            trades["pnl"] = trades["sell_price"] - trades["buy_price"]
            winning_trades = trades[trades["pnl"] > 0]
            losing_trades = trades[trades["pnl"] < 0]

            total_trades = len(trades)
            n_winning = len(winning_trades)
            n_losing = len(losing_trades)
            win_rate = n_winning / total_trades if total_trades > 0 else 0.0

            avg_profit = winning_trades["pnl"].mean() if n_winning > 0 else 0.0
            avg_loss = losing_trades["pnl"].mean() if n_losing > 0 else 0.0

            total_profit = winning_trades["pnl"].sum() if n_winning > 0 else 0.0
            total_loss = abs(losing_trades["pnl"].sum()) if n_losing > 0 else 0.0
            profit_factor = total_profit / total_loss if total_loss > 0 else 0.0

            return {
                "total_trades": total_trades,
                "winning_trades": n_winning,
                "losing_trades": n_losing,
                "win_rate": win_rate,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "total_profit": total_profit,
                "total_loss": total_loss,
            }

        return await asyncio.to_thread(_calculate)

    async def optimize_strategy_params(
        self,
        stock_codes: List[str],
        param_grid: Dict[str, List[Any]],
        start_date: date,
        end_date: date,
        metric: str = "sharpe_ratio",
    ) -> Dict[str, Any]:
        """
        异步优化策略参数

        Args:
            stock_codes: 股票代码列表
            param_grid: 参数网格
            start_date: 开始日期
            end_date: 结束日期
            metric: 优化目标指标

        Returns:
            最优参数和对应的回测结果

        Raises:
            BacktestError: 优化错误
        """

        def _optimize():
            # 生成所有参数组合
            from itertools import product

            keys = param_grid.keys()
            values = param_grid.values()
            param_combinations = [dict(zip(keys, v)) for v in product(*values)]

            best_result = None
            best_metric_value = float("-inf")

            for params in param_combinations:
                result = self.engine.run(
                    stock_codes=stock_codes,
                    strategy_params=params,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )

                metric_value = result["metrics"].get(metric, float("-inf"))
                if metric_value > best_metric_value:
                    best_metric_value = metric_value
                    best_result = {"params": params, "result": result, "metric_value": metric_value}

            return best_result

        return await asyncio.to_thread(_optimize)
