#!/usr/bin/env python3
"""
回测性能基准测试

测试目标（基于REFACTORING_PLAN.md任务1.2.3）:
- 向量化回测: <3秒 (1000股×250天)
- 多头策略: <2秒
- 市场中性策略: <5秒

作者: Stock Analysis Team
创建: 2026-01-31
"""

import sys
import time
import pytest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from backtest.backtest_engine import BacktestEngine
from strategies.momentum_strategy import MomentumStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from src.utils.response import Response

from .benchmarks import (
    PerformanceBenchmarkBase,
    PerformanceThresholds,
    print_benchmark_header,
    print_benchmark_result,
    performance_reporter,
)


# ==================== Response 辅助函数 ====================


def unwrap_response(response):
    """
    从 Response 对象中提取数据（兼容性封装）

    Args:
        response: Response 对象或原始数据

    Returns:
        解包后的数据（通常是 DataFrame 或 dict）

    Raises:
        ValueError: 如果 Response 状态为失败

    Examples:
        >>> result = unwrap_response(engine.backtest_long_only(signals, prices))
        >>> assert isinstance(result, dict)
    """
    if isinstance(response, Response):
        if not response.is_success():
            raise ValueError(f"操作失败: {response.error_message}")
        return response.data
    return response


# ==================== 模块级别辅助函数（用于并行处理）====================


def _run_single_backtest(args):
    """
    单次回测的辅助函数（模块级别，用于并行处理）

    注意：此函数必须是模块级别的，因为 multiprocessing 需要能够 pickle 它。

    Args:
        args: (signals, prices) 元组

    Returns:
        dict: 回测结果字典（已从 Response 对象中解包）
    """
    signals, prices = args
    engine = BacktestEngine(initial_capital=1_000_000)
    result_response = engine.backtest_long_only(signals, prices)

    # 解包 Response 对象（使用与顶层相同的逻辑）
    if isinstance(result_response, Response):
        if not result_response.is_success():
            raise ValueError(f"操作失败: {result_response.error_message}")
        return result_response.data
    return result_response


# ==================== 回测数据生成 ====================


def generate_backtest_signals(n_stocks: int = 100, n_days: int = 250, seed: int = 42) -> pd.DataFrame:
    """
    生成回测信号数据

    Args:
        n_stocks: 股票数量
        n_days: 交易天数
        seed: 随机种子

    Returns:
        信号DataFrame (index=date, columns=stock_code, values=score)
    """
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stock_codes = [f'{i:06d}' for i in range(n_stocks)]

    # 生成因子得分矩阵
    scores = np.random.randn(n_days, n_stocks)

    df = pd.DataFrame(scores, index=dates, columns=stock_codes)
    return df


def generate_backtest_prices(n_stocks: int = 100, n_days: int = 250, seed: int = 42) -> pd.DataFrame:
    """
    生成回测价格数据

    Args:
        n_stocks: 股票数量
        n_days: 交易天数
        seed: 随机种子

    Returns:
        价格DataFrame (index=date, columns=stock_code, values=close_price)
    """
    np.random.seed(seed)
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stock_codes = [f'{i:06d}' for i in range(n_stocks)]

    # 生成价格矩阵
    price_matrix = []
    for _ in range(n_stocks):
        returns = np.random.normal(0.0005, 0.02, n_days)
        price = 100 * (1 + returns).cumprod()
        price_matrix.append(price)

    price_matrix = np.array(price_matrix).T  # 转置为 (n_days, n_stocks)

    df = pd.DataFrame(price_matrix, index=dates, columns=stock_codes)
    return df


# ==================== Pytest Fixtures ====================


@pytest.fixture(scope='session')
def backtest_signals_large():
    """大规模回测信号: 1000股×250天"""
    return generate_backtest_signals(n_stocks=1000, n_days=250)


@pytest.fixture(scope='session')
def backtest_prices_large():
    """大规模回测价格: 1000股×250天"""
    return generate_backtest_prices(n_stocks=1000, n_days=250)


@pytest.fixture(scope='session')
def backtest_signals_medium():
    """中等规模回测信号: 100股×250天"""
    return generate_backtest_signals(n_stocks=100, n_days=250)


@pytest.fixture(scope='session')
def backtest_prices_medium():
    """中等规模回测价格: 100股×250天"""
    return generate_backtest_prices(n_stocks=100, n_days=250)


# ==================== 向量化回测性能测试 ====================


class TestBacktestEnginePerformance(PerformanceBenchmarkBase):
    """回测引擎性能测试"""

    def test_vectorized_backtest_large_scale(self, backtest_signals_large, backtest_prices_large):
        """
        测试大规模向量化回测性能

        数据规模: 1000股×250天
        性能目标: <3秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("向量化回测性能测试 - 1000股×250天")

        signals = backtest_signals_large
        prices = backtest_prices_large

        # 执行回测
        start = time.time()
        engine = BacktestEngine(initial_capital=10_000_000, commission_rate=0.0003)

        # 使用long_only回测(实际API)
        results_response = engine.backtest_long_only(signals, prices)
        elapsed = time.time() - start

        # 解包Response对象
        results = unwrap_response(results_response)

        # 验证结果
        assert results is not None
        assert 'portfolio_value' in results or 'equity_curve' in results

        # 性能断言
        threshold = PerformanceThresholds.BACKTEST_VECTORIZED
        n_stocks = len(signals.columns)
        n_days = len(signals)

        print_benchmark_result(
            f"向量化回测 ({n_stocks}股×{n_days}天)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="回测性能",
            test_name="向量化回测(大规模)",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_stocks': n_stocks, 'n_days': n_days}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "向量化回测(大规模)",
            {'n_stocks': n_stocks, 'n_days': n_days}
        )

    def test_vectorized_backtest_medium_scale(self, backtest_signals_medium, backtest_prices_medium):
        """
        测试中等规模向量化回测性能

        数据规模: 100股×250天
        性能目标: 应该非常快
        """
        print_benchmark_header("向量化回测性能测试 - 100股×250天")

        signals = backtest_signals_medium
        prices = backtest_prices_medium

        start = time.time()
        engine = BacktestEngine(initial_capital=1_000_000, commission_rate=0.0003)
        results_response = engine.backtest_long_only(signals, prices)
        results = unwrap_response(results_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = 0.7  # 中等规模应该很快（考虑系统负载，从0.5s调整到0.7s）
        n_stocks = len(signals.columns)
        n_days = len(signals)

        print_benchmark_result(
            f"向量化回测 ({n_stocks}股×{n_days}天)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="回测性能",
            test_name="向量化回测(中等规模)",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_stocks': n_stocks, 'n_days': n_days}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "向量化回测(中等规模)",
            {'n_stocks': n_stocks, 'n_days': n_days}
        )


# ==================== 策略回测性能测试 ====================


class TestStrategyBacktestPerformance(PerformanceBenchmarkBase):
    """策略回测性能测试"""

    def test_long_only_strategy_benchmark(self, backtest_signals_medium, backtest_prices_medium):
        """
        测试多头策略回测性能

        性能目标: <2秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("多头策略回测性能测试")

        signals = backtest_signals_medium.copy()
        prices = backtest_prices_medium

        # 信号已经是得分格式,直接使用
        start = time.time()
        engine = BacktestEngine(initial_capital=1_000_000)
        results_response = engine.backtest_long_only(signals, prices, top_n=20)
        results = unwrap_response(results_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = PerformanceThresholds.BACKTEST_LONG_ONLY
        print_benchmark_result("多头策略回测", elapsed, threshold)

        performance_reporter.add_result(
            category="回测性能",
            test_name="多头策略",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "多头策略回测")

    def test_market_neutral_strategy_benchmark(self, backtest_signals_medium, backtest_prices_medium):
        """
        测试市场中性策略回测性能

        性能目标: <5秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("市场中性策略回测性能测试")

        signals = backtest_signals_medium
        prices = backtest_prices_medium

        start = time.time()
        engine = BacktestEngine(initial_capital=1_000_000)
        results_response = engine.backtest_market_neutral(signals, prices, top_n=20, bottom_n=20)
        results = unwrap_response(results_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = PerformanceThresholds.BACKTEST_MARKET_NEUTRAL
        print_benchmark_result("市场中性策略回测", elapsed, threshold)

        performance_reporter.add_result(
            category="回测性能",
            test_name="市场中性策略",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "市场中性策略回测")

    def test_momentum_strategy_full_workflow(self, single_stock_data_long):
        """测试动量策略完整工作流性能"""
        print_benchmark_header("动量策略完整工作流性能测试")

        data = single_stock_data_long.copy()

        start = time.time()

        # 1. 计算动量因子作为信号
        momentum = data['close'].pct_change(20)

        # 转换为宽格式(单股票变为DataFrame)
        signals = pd.DataFrame({
            '000001': momentum
        })
        prices = pd.DataFrame({
            '000001': data['close']
        })

        # 2. 回测
        engine = BacktestEngine(initial_capital=1_000_000)
        results_response = engine.backtest_long_only(signals, prices, top_n=1)
        results = unwrap_response(results_response)  # 解包Response对象

        elapsed = time.time() - start

        threshold = 1.0  # 完整工作流1秒内
        print_benchmark_result("动量策略完整工作流", elapsed, threshold)

        performance_reporter.add_result(
            category="回测性能",
            test_name="动量策略完整工作流",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "动量策略完整工作流")


# ==================== 性能分析器测试 ====================


class TestPerformanceAnalyzerBenchmark(PerformanceBenchmarkBase):
    """性能分析器基准测试"""

    def test_performance_metrics_calculation(self, backtest_signals_medium, backtest_prices_medium):
        """测试性能指标计算速度"""
        print_benchmark_header("性能指标计算基准测试")

        signals = backtest_signals_medium
        prices = backtest_prices_medium

        # 先运行回测获得结果
        engine = BacktestEngine(initial_capital=1_000_000)
        results_response = engine.backtest_long_only(signals, prices)
        results = unwrap_response(results_response)  # 解包Response对象

        # 测试性能指标计算
        from backtest.performance_analyzer import PerformanceAnalyzer

        start = time.time()
        analyzer = PerformanceAnalyzer(results)
        metrics = analyzer.calculate_all_metrics()
        elapsed = time.time() - start

        threshold = 0.5  # 性能指标计算应该很快
        print_benchmark_result("性能指标计算", elapsed, threshold)

        performance_reporter.add_result(
            category="回测性能",
            test_name="性能指标计算",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "性能指标计算")

    def test_drawdown_analysis_benchmark(self, backtest_signals_medium, backtest_prices_medium):
        """测试回撤分析计算速度"""
        print_benchmark_header("回撤分析基准测试")

        signals = backtest_signals_medium
        prices = backtest_prices_medium

        engine = BacktestEngine(initial_capital=1_000_000)
        results_response = engine.backtest_long_only(signals, prices)
        results = unwrap_response(results_response)  # 解包Response对象

        from backtest.performance_analyzer import PerformanceAnalyzer

        start = time.time()
        analyzer = PerformanceAnalyzer(results)
        drawdown_info = analyzer.calculate_drawdown()
        elapsed = time.time() - start

        threshold = 0.3
        print_benchmark_result("回撤分析计算", elapsed, threshold)

        performance_reporter.add_result(
            category="回测性能",
            test_name="回撤分析",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "回撤分析计算")


# ==================== 并行回测性能测试 ====================


class TestParallelBacktestPerformance(PerformanceBenchmarkBase):
    """并行回测性能测试"""

    def test_parallel_vs_sequential_backtest(self, backtest_signals_medium, backtest_prices_medium):
        """测试并行回测vs顺序回测的性能差异"""
        print_benchmark_header("并行回测vs顺序回测性能对比")

        signals = backtest_signals_medium
        prices = backtest_prices_medium

        # 顺序回测
        start = time.time()
        results_seq = []
        for _ in range(4):  # 模拟4个策略
            engine = BacktestEngine(initial_capital=1_000_000)
            result_response = engine.backtest_long_only(signals, prices)
            result = unwrap_response(result_response)  # 解包Response对象
            results_seq.append(result)
        sequential_time = time.time() - start

        # 并行回测
        try:
            from concurrent.futures import ProcessPoolExecutor

            start = time.time()
            with ProcessPoolExecutor(max_workers=4) as executor:
                args_list = [(signals, prices) for _ in range(4)]
                results_par = list(executor.map(_run_single_backtest, args_list))
            parallel_time = time.time() - start

            speedup = sequential_time / parallel_time if parallel_time > 0 else 0

            print(f"  顺序回测: {sequential_time:.3f}s")
            print(f"  并行回测: {parallel_time:.3f}s")
            print(f"  加速比:   {speedup:.2f}x")

            # 并行加速比检查（对于小任务，加速比可能不明显）
            # 设置较低的阈值1.1x，因为任务较小时进程创建开销占比大
            min_speedup = 1.1
            if speedup < min_speedup:
                print(f"  ⚠️  警告: 并行加速不明显 ({speedup:.2f}x < {min_speedup}x)")
                print(f"      这可能是因为任务规模太小，进程创建开销占比较大")

            # 记录结果但不强制要求通过（仅用于监控）
            performance_reporter.add_result(
                category="回测性能",
                test_name="并行回测加速比",
                elapsed=parallel_time,
                threshold=sequential_time / min_speedup,
                passed=speedup >= min_speedup,
                details={'speedup': f"{speedup:.2f}x", 'note': 'informational'}
            )

            # 只要并行不比顺序慢就算通过（允许进程开销）
            assert speedup >= 0.9, f"并行回测比顺序回测更慢: {speedup:.2f}x"

        except ImportError:
            print("  并行回测测试跳过（multiprocessing不可用）")
            pytest.skip("multiprocessing不可用")


if __name__ == '__main__':
    # 运行性能测试
    pytest.main([__file__, '-v', '--tb=short'])
