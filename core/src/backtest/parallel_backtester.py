#!/usr/bin/env python3
"""
并行回测执行器

支持同时回测多个策略，自动对比绩效指标，生成详细报告。

主要功能：
1. 并行回测多个策略（利用多核CPU加速）
2. 自动生成策略对比报告
3. 支持灵活的并行配置
4. 完整的错误处理和日志记录

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from loguru import logger
import time
import warnings

warnings.filterwarnings('ignore')

from src.utils.parallel_executor import ParallelExecutor
from src.config.features import ParallelComputingConfig
from src.backtest.backtest_engine import BacktestEngine
from src.strategies.base_strategy import BaseStrategy


# ==================== 数据类 ====================

@dataclass
class BacktestTask:
    """
    单个策略回测任务

    封装回测所需的所有信息，确保可序列化（multiprocessing需要）
    """
    strategy_name: str
    strategy_class_name: str
    strategy_config: Dict[str, Any]
    prices: pd.DataFrame
    features: Optional[pd.DataFrame] = None
    backtest_params: Dict[str, Any] = field(default_factory=dict)
    engine_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转为字典（便于日志和调试）"""
        return {
            'strategy_name': self.strategy_name,
            'strategy_class': self.strategy_class_name,
            'data_shape': f"{self.prices.shape}",
            'backtest_params': self.backtest_params,
            'engine_params': self.engine_params
        }


@dataclass
class BacktestResult:
    """
    单个策略回测结果

    包含完整的回测输出和元数据
    """
    strategy_name: str
    success: bool
    result: Optional[Dict] = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def get_metrics(self) -> Dict[str, float]:
        """提取关键指标"""
        if not self.success or self.result is None:
            return {}

        metrics = self.result.get('metrics', {})
        return {
            'annual_return': metrics.get('annual_return', 0.0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
            'max_drawdown': metrics.get('max_drawdown', 0.0),
            'win_rate': metrics.get('win_rate', 0.0),
            'calmar_ratio': metrics.get('calmar_ratio', 0.0),
            'sortino_ratio': metrics.get('sortino_ratio', 0.0),
            'total_return': metrics.get('total_return', 0.0)
        }


# ==================== 核心类 ====================

class ParallelBacktester:
    """
    并行回测执行器

    核心功能：
    1. 并行执行多个策略的回测
    2. 自动生成策略对比报告
    3. 智能的资源管理和错误处理

    Example:
        >>> from strategies.predefined.momentum_strategy import MomentumStrategy
        >>> from strategies.predefined.mean_reversion_strategy import MeanReversionStrategy
        >>>
        >>> strategies = [
        ...     MomentumStrategy("动量策略", {'lookback': 20}),
        ...     MeanReversionStrategy("均值回归", {'lookback': 10})
        ... ]
        >>>
        >>> backtester = ParallelBacktester(n_workers=4)
        >>> results = backtester.run(strategies, prices_df)
        >>> report = backtester.generate_comparison_report(results)
        >>> print(report)
    """

    def __init__(
        self,
        parallel_config: Optional[ParallelComputingConfig] = None,
        n_workers: int = -1,
        show_progress: bool = True,
        verbose: bool = True
    ):
        """
        初始化并行回测器

        Args:
            parallel_config: 并行计算配置（优先级最高）
            n_workers: worker数量（-1=自动检测，1=串行）
            show_progress: 是否显示进度条
            verbose: 是否显示详细日志
        """
        if parallel_config is None:
            parallel_config = ParallelComputingConfig(
                enable_parallel=True,
                n_workers=n_workers,
                show_progress=show_progress,
                parallel_backend='multiprocessing'  # 回测使用多进程
            )

        self.parallel_config = parallel_config
        self.verbose = verbose

        if verbose:
            logger.info(
                f"初始化并行回测器: n_workers={parallel_config.n_workers}, "
                f"backend={parallel_config.parallel_backend}"
            )

    def run(
        self,
        strategies: List[BaseStrategy],
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **backtest_kwargs
    ) -> Dict[str, BacktestResult]:
        """
        并行回测多个策略

        Args:
            strategies: 策略列表
            prices: 价格数据 (index=date, columns=stock_codes)
            features: 特征数据（可选，某些策略需要）
            **backtest_kwargs: 传递给回测引擎的额外参数，如：
                - initial_capital: 初始资金
                - commission_rate: 佣金率
                - top_n: 选股数量
                - holding_period: 持仓周期
                - rebalance_freq: 调仓频率

        Returns:
            {strategy_name: BacktestResult} 字典
        """
        if not strategies:
            logger.warning("策略列表为空")
            return {}

        logger.info(f"\n{'='*70}")
        logger.info(f"开始并行回测 {len(strategies)} 个策略")
        logger.info(f"{'='*70}")

        # 准备任务
        tasks = self._prepare_tasks(strategies, prices, features, backtest_kwargs)

        if self.verbose:
            for i, task in enumerate(tasks, 1):
                logger.info(f"任务 {i}: {task.strategy_name}")

        # 执行并行回测
        start_time = time.time()

        try:
            with ParallelExecutor(self.parallel_config) as executor:
                results_list = executor.map(
                    self._run_single_backtest,
                    tasks,
                    desc="回测策略"
                )
        except Exception as e:
            logger.error(f"并行回测执行失败: {e}")
            # 降级到串行执行
            logger.warning("降级到串行执行...")
            results_list = [self._run_single_backtest(task) for task in tasks]

        total_time = time.time() - start_time

        # 整理结果
        results = {}
        success_count = 0

        for result in results_list:
            results[result.strategy_name] = result
            if result.success:
                success_count += 1

        # 输出统计
        logger.info(f"\n{'='*70}")
        logger.success(
            f"并行回测完成！成功: {success_count}/{len(strategies)}, "
            f"总耗时: {total_time:.2f}秒"
        )
        logger.info(f"{'='*70}\n")

        # 输出每个策略的结果摘要
        if self.verbose:
            self._print_results_summary(results)

        return results

    def _prepare_tasks(
        self,
        strategies: List[BaseStrategy],
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame],
        backtest_kwargs: Dict
    ) -> List[BacktestTask]:
        """
        准备回测任务

        将策略对象转换为可序列化的任务对象
        """
        tasks = []

        # 分离引擎参数和回测参数
        engine_params = {
            k: v for k, v in backtest_kwargs.items()
            if k in ['initial_capital', 'commission_rate', 'stamp_tax_rate',
                     'min_commission', 'slippage', 'slippage_model']
        }

        backtest_params = {
            k: v for k, v in backtest_kwargs.items()
            if k in ['top_n', 'holding_period', 'rebalance_freq']
        }

        for strategy in strategies:
            task = BacktestTask(
                strategy_name=strategy.name,
                strategy_class_name=strategy.__class__.__name__,
                strategy_config=strategy.config.to_dict(),
                prices=prices.copy(),  # 避免共享内存问题
                features=features.copy() if features is not None else None,
                backtest_params=backtest_params,
                engine_params=engine_params
            )
            tasks.append(task)

        return tasks

    @staticmethod
    def _run_single_backtest(task: BacktestTask) -> BacktestResult:
        """
        执行单个策略回测（静态方法，可序列化）

        Args:
            task: 回测任务

        Returns:
            BacktestResult对象
        """
        start_time = time.time()

        try:
            # 1. 重建策略对象
            strategy = ParallelBacktester._rebuild_strategy(task)

            # 2. 生成信号
            if task.features is not None:
                signals = strategy.generate_signals(task.prices, task.features)
            else:
                signals = strategy.generate_signals(task.prices)

            # 3. 创建回测引擎
            engine = BacktestEngine(
                verbose=False,  # 并行时关闭详细输出
                **task.engine_params
            )

            # 4. 执行回测
            # 从策略配置或任务参数中获取回测参数
            top_n = task.backtest_params.get('top_n', strategy.config.top_n)
            holding_period = task.backtest_params.get(
                'holding_period',
                strategy.config.holding_period
            )
            rebalance_freq = task.backtest_params.get(
                'rebalance_freq',
                strategy.config.rebalance_freq
            )

            result = engine.backtest_long_only(
                signals=signals,
                prices=task.prices,
                top_n=top_n,
                holding_period=holding_period,
                rebalance_freq=rebalance_freq
            )

            execution_time = time.time() - start_time

            # 统一处理Response对象：回测引擎返回Response对象，需要提取data字段
            if hasattr(result, 'data') and hasattr(result, 'is_success'):
                if not result.is_success():
                    raise ValueError(f"回测失败: {result.error}")
                result_data = result.data
            else:
                # 向后兼容：如果直接返回dict则使用原值
                result_data = result

            return BacktestResult(
                strategy_name=task.strategy_name,
                success=True,
                result=result_data,
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"

            logger.error(f"策略 {task.strategy_name} 回测失败: {error_msg}")

            return BacktestResult(
                strategy_name=task.strategy_name,
                success=False,
                error=error_msg,
                execution_time=execution_time
            )

    @staticmethod
    def _rebuild_strategy(task: BacktestTask) -> BaseStrategy:
        """
        从任务重建策略对象

        Args:
            task: 回测任务

        Returns:
            策略对象
        """
        # 动态导入策略类
        from strategies.predefined.momentum_strategy import MomentumStrategy
        from strategies.predefined.mean_reversion_strategy import MeanReversionStrategy
        from strategies.predefined.multi_factor_strategy import MultiFactorStrategy
        # 注意: MLStrategy 已被删除，请使用新的 ml.MLEntry
        # from strategies.ml_strategy import MLStrategy

        strategy_classes = {
            'MomentumStrategy': MomentumStrategy,
            'MeanReversionStrategy': MeanReversionStrategy,
            'MultiFactorStrategy': MultiFactorStrategy,
            # 'MLStrategy': MLStrategy  # 已废弃，使用 ml.MLEntry
        }

        strategy_class = strategy_classes.get(task.strategy_class_name)

        if strategy_class is None:
            raise ValueError(
                f"未知的策略类: {task.strategy_class_name}。"
                f"支持的策略: {list(strategy_classes.keys())}"
            )

        # 重建策略
        strategy = strategy_class(
            name=task.strategy_name,
            config=task.strategy_config
        )

        return strategy

    def _print_results_summary(self, results: Dict[str, BacktestResult]):
        """打印结果摘要"""
        logger.info("\n策略回测结果摘要:")
        logger.info("-" * 70)

        for name, result in results.items():
            if result.success:
                metrics = result.get_metrics()
                logger.success(
                    f"{name:20s} | "
                    f"年化收益: {metrics.get('annual_return', 0)*100:6.2f}% | "
                    f"夏普: {metrics.get('sharpe_ratio', 0):5.2f} | "
                    f"最大回撤: {metrics.get('max_drawdown', 0)*100:6.2f}% | "
                    f"耗时: {result.execution_time:.2f}s"
                )
            else:
                logger.error(f"{name:20s} | 失败: {result.error}")

        logger.info("-" * 70)

    def generate_comparison_report(
        self,
        results: Dict[str, BacktestResult],
        metrics_to_compare: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        生成策略对比报告

        Args:
            results: 回测结果字典
            metrics_to_compare: 要对比的指标列表（None=全部）

        Returns:
            对比报告 DataFrame
        """
        if metrics_to_compare is None:
            metrics_to_compare = [
                'annual_return',
                'sharpe_ratio',
                'max_drawdown',
                'win_rate',
                'calmar_ratio',
                'sortino_ratio',
                'total_return'
            ]

        metrics_list = []

        for strategy_name, result in results.items():
            if not result.success:
                # 失败的策略用NaN填充
                metrics_dict = {
                    '策略名称': strategy_name,
                    '状态': '失败',
                    '错误信息': result.error
                }
                for metric in metrics_to_compare:
                    metrics_dict[self._format_metric_name(metric)] = np.nan

                metrics_list.append(metrics_dict)
                continue

            # 提取指标
            result_metrics = result.get_metrics()

            metrics_dict = {
                '策略名称': strategy_name,
                '状态': '成功',
                '执行时间(秒)': round(result.execution_time, 2)
            }

            for metric in metrics_to_compare:
                value = result_metrics.get(metric, 0.0)
                # 百分比指标转换
                if metric in ['annual_return', 'max_drawdown', 'win_rate', 'total_return']:
                    value = value * 100

                metrics_dict[self._format_metric_name(metric)] = round(value, 4)

            metrics_list.append(metrics_dict)

        # 创建DataFrame
        df = pd.DataFrame(metrics_list)

        # 按夏普比率排序（如果存在）
        if '夏普比率' in df.columns:
            df = df.sort_values('夏普比率', ascending=False)

        logger.info("\n" + "="*70)
        logger.info("策略对比报告")
        logger.info("="*70)
        logger.info(f"\n{df.to_string(index=False)}\n")

        return df

    @staticmethod
    def _format_metric_name(metric: str) -> str:
        """格式化指标名称"""
        name_map = {
            'annual_return': '年化收益率(%)',
            'sharpe_ratio': '夏普比率',
            'max_drawdown': '最大回撤(%)',
            'win_rate': '胜率(%)',
            'calmar_ratio': '卡玛比率',
            'sortino_ratio': '索提诺比率',
            'total_return': '总收益率(%)'
        }
        return name_map.get(metric, metric)

    def save_comparison_report(
        self,
        results: Dict[str, BacktestResult],
        save_path: str,
        format: str = 'csv'
    ):
        """
        保存对比报告到文件

        Args:
            results: 回测结果
            save_path: 保存路径
            format: 格式 ('csv', 'excel', 'html')
        """
        df = self.generate_comparison_report(results)

        if format == 'csv':
            df.to_csv(save_path, index=False, encoding='utf-8-sig')
        elif format == 'excel':
            df.to_excel(save_path, index=False)
        elif format == 'html':
            df.to_html(save_path, index=False)
        else:
            raise ValueError(f"不支持的格式: {format}")

        logger.success(f"对比报告已保存: {save_path}")


# ==================== 便捷函数 ====================

def parallel_backtest(
    strategies: List[BaseStrategy],
    prices: pd.DataFrame,
    features: Optional[pd.DataFrame] = None,
    n_workers: int = -1,
    show_progress: bool = True,
    **backtest_kwargs
) -> Dict[str, BacktestResult]:
    """
    便捷函数：并行回测多个策略

    Args:
        strategies: 策略列表
        prices: 价格数据
        features: 特征数据（可选）
        n_workers: worker数量
        show_progress: 是否显示进度
        **backtest_kwargs: 回测参数

    Returns:
        回测结果字典

    Example:
        >>> results = parallel_backtest(
        ...     [strategy1, strategy2, strategy3],
        ...     prices_df,
        ...     n_workers=4,
        ...     initial_capital=1000000,
        ...     top_n=50
        ... )
    """
    backtester = ParallelBacktester(
        n_workers=n_workers,
        show_progress=show_progress
    )

    return backtester.run(
        strategies=strategies,
        prices=prices,
        features=features,
        **backtest_kwargs
    )
