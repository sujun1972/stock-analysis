#!/usr/bin/env python3
"""
三层架构性能测试（T8任务）

测试三层架构的性能表现，包括：
- 回测速度基准测试（目标：100股票×3年 < 30秒）
- 内存占用分析（目标：< 2GB）
- 大规模数据测试（1000+股票）
- 性能瓶颈识别
- 不同策略组合的性能对比

Author: Stock Analysis Core Team
Date: 2026-02-06
Task: T8 - Performance Testing
"""

import pytest
import pandas as pd
import numpy as np
import time
import psutil
import os
from datetime import datetime
from typing import Dict, List, Tuple

from src.backtest.backtest_engine import BacktestEngine
from src.strategies.three_layer.selectors import (
    MomentumSelector,
    ValueSelector,
    ExternalSelector
)
from src.strategies.three_layer.entries import (
    MABreakoutEntry,
    RSIOversoldEntry,
    ImmediateEntry
)
from src.strategies.three_layer.exits import (
    ATRStopLossExit,
    FixedStopLossExit,
    TimeBasedExit,
    CombinedExit
)


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.metrics = []

    def record(self, test_name: str, n_stocks: int, n_days: int,
               elapsed_time: float, memory_mb: float, n_trades: int = None):
        """记录性能指标"""
        self.metrics.append({
            'test_name': test_name,
            'n_stocks': n_stocks,
            'n_days': n_days,
            'elapsed_time': elapsed_time,
            'memory_mb': memory_mb,
            'n_trades': n_trades,
            'stocks_per_sec': n_stocks / elapsed_time if elapsed_time > 0 else 0,
            'days_per_sec': n_days / elapsed_time if elapsed_time > 0 else 0
        })

    def get_summary(self) -> pd.DataFrame:
        """获取性能汇总"""
        return pd.DataFrame(self.metrics)

    def print_summary(self):
        """打印性能汇总"""
        df = self.get_summary()
        print("\n" + "="*80)
        print("性能测试汇总报告")
        print("="*80)
        for _, row in df.iterrows():
            print(f"\n测试: {row['test_name']}")
            print(f"  股票数: {row['n_stocks']}")
            print(f"  天数: {row['n_days']}")
            print(f"  耗时: {row['elapsed_time']:.2f}秒")
            print(f"  内存占用: {row['memory_mb']:.1f}MB")
            if row['n_trades'] is not None:
                print(f"  交易次数: {row['n_trades']}")
            print(f"  处理速度: {row['stocks_per_sec']:.1f}股票/秒, {row['days_per_sec']:.1f}天/秒")
        print("="*80)


# 全局性能指标收集器
performance_metrics = PerformanceMetrics()


def get_memory_usage() -> float:
    """获取当前进程的内存占用（MB）"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def generate_price_data(n_stocks: int, n_days: int, seed: int = 42) -> pd.DataFrame:
    """
    生成测试用的价格数据

    Args:
        n_stocks: 股票数量
        n_days: 天数
        seed: 随机种子

    Returns:
        价格DataFrame
    """
    np.random.seed(seed)
    dates = pd.date_range('2020-01-01', periods=n_days, freq='D')

    # 生成股票代码
    stocks = []
    for i in range(n_stocks):
        if i < 1000:
            stocks.append(f'60{i:04d}.SH')
        elif i < 2000:
            stocks.append(f'00{i-1000:04d}.SZ')
        else:
            stocks.append(f'30{i-2000:04d}.SZ')

    stocks = stocks[:n_stocks]

    # 生成价格数据
    prices = pd.DataFrame(index=dates, columns=stocks, dtype=float)

    for i, stock in enumerate(stocks):
        # 不同股票有不同的趋势和波动率
        base_price = 10 + (i % 50)
        trend = np.linspace(0, (i % 10) * 0.1, n_days)
        noise = np.random.randn(n_days) * 0.5
        prices[stock] = base_price * (1 + trend + noise * 0.01)

    return prices


@pytest.fixture
def small_dataset():
    """小数据集：10股票 × 60天"""
    return generate_price_data(10, 60)


@pytest.fixture
def medium_dataset():
    """中等数据集：100股票 × 252天（1年）"""
    return generate_price_data(100, 252)


@pytest.fixture
def large_dataset():
    """大数据集：100股票 × 756天（3年）"""
    return generate_price_data(100, 756)


@pytest.fixture
def xlarge_dataset():
    """超大数据集：500股票 × 756天（3年）"""
    return generate_price_data(500, 756)


class TestBacktestSpeedBenchmark:
    """回测速度基准测试"""

    def test_baseline_speed_10_stocks_60_days(self, small_dataset):
        """
        基线测试：10股票 × 60天

        用于建立性能基线
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        mem_before = get_memory_usage()
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=small_dataset,
            start_date=small_dataset.index[20],
            end_date=small_dataset.index[-1],
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before

        assert result.is_success()

        n_trades = result.data['metrics']['n_trades']
        performance_metrics.record(
            '基线测试_10股票_60天',
            10, 60, elapsed_time, mem_used, n_trades
        )

        print(f"\n基线测试结果:")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  内存增量: {mem_used:.1f}MB")
        print(f"  交易次数: {n_trades}")

    def test_medium_scale_100_stocks_1_year(self, medium_dataset):
        """
        中等规模测试：100股票 × 1年

        目标：< 15秒
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        mem_before = get_memory_usage()
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=medium_dataset,
            start_date=medium_dataset.index[20],
            end_date=medium_dataset.index[-1],
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before

        assert result.is_success()

        n_trades = result.data['metrics']['n_trades']
        performance_metrics.record(
            '中等规模_100股票_1年',
            100, 252, elapsed_time, mem_used, n_trades
        )

        print(f"\n中等规模测试结果:")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  内存增量: {mem_used:.1f}MB")
        print(f"  交易次数: {n_trades}")

        # 验证性能目标
        assert elapsed_time < 15, f"性能未达标：耗时{elapsed_time:.2f}秒 > 15秒"

    def test_benchmark_100_stocks_3_years(self, large_dataset):
        """
        基准测试：100股票 × 3年（核心性能指标）

        目标：< 30秒
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        mem_before = get_memory_usage()
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=large_dataset,
            start_date=large_dataset.index[20],
            end_date=large_dataset.index[-1],
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before

        assert result.is_success()

        n_trades = result.data['metrics']['n_trades']
        performance_metrics.record(
            '基准测试_100股票_3年',
            100, 756, elapsed_time, mem_used, n_trades
        )

        print(f"\n⭐ 基准测试结果（核心指标）:")
        print(f"  耗时: {elapsed_time:.2f}秒 (目标: < 30秒)")
        print(f"  内存增量: {mem_used:.1f}MB (目标: < 2048MB)")
        print(f"  交易次数: {n_trades}")
        print(f"  状态: {'✅ 达标' if elapsed_time < 30 else '❌ 未达标'}")

        # 验证性能目标
        assert elapsed_time < 30, f"性能未达标：耗时{elapsed_time:.2f}秒 > 30秒"
        assert mem_used < 2048, f"内存超标：{mem_used:.1f}MB > 2048MB"


class TestMemoryUsage:
    """内存占用分析"""

    def test_memory_footprint_100_stocks(self, large_dataset):
        """
        测试100股票×3年的内存占用

        目标：< 2GB
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        # 测量初始内存
        mem_initial = get_memory_usage()

        # 执行回测
        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=large_dataset,
            start_date=large_dataset.index[20],
            end_date=large_dataset.index[-1],
            rebalance_freq='W'
        )

        # 测量峰值内存
        mem_peak = get_memory_usage()
        mem_used = mem_peak - mem_initial

        assert result.is_success()

        print(f"\n内存占用分析:")
        print(f"  初始内存: {mem_initial:.1f}MB")
        print(f"  峰值内存: {mem_peak:.1f}MB")
        print(f"  内存增量: {mem_used:.1f}MB")
        print(f"  数据集大小: 100股票 × 756天")
        print(f"  状态: {'✅ 达标' if mem_used < 2048 else '❌ 超标'}")

        # 验证内存目标
        assert mem_used < 2048, f"内存超标：{mem_used:.1f}MB > 2048MB"

    def test_memory_scaling(self):
        """
        测试内存占用的扩展性

        验证内存增长是否线性
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 5})
        entry = ImmediateEntry(params={'max_stocks': 5})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        test_configs = [
            (10, 60, '10股票_60天'),
            (50, 252, '50股票_1年'),
            (100, 252, '100股票_1年'),
        ]

        results = []

        for n_stocks, n_days, label in test_configs:
            prices = generate_price_data(n_stocks, n_days)

            mem_before = get_memory_usage()

            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=prices,
                start_date=prices.index[20],
                end_date=prices.index[-1],
                rebalance_freq='W'
            )

            mem_after = get_memory_usage()
            mem_used = mem_after - mem_before

            assert result.is_success()

            results.append({
                'label': label,
                'n_stocks': n_stocks,
                'n_days': n_days,
                'memory_mb': mem_used
            })

        print(f"\n内存扩展性测试:")
        for r in results:
            print(f"  {r['label']}: {r['memory_mb']:.1f}MB")


class TestLargeScaleBacktest:
    """大规模数据测试"""

    def test_500_stocks_3_years(self, xlarge_dataset):
        """
        大规模测试：500股票 × 3年

        验证系统在大规模数据下的稳定性
        """
        engine = BacktestEngine(initial_capital=10000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 20})
        entry = ImmediateEntry(params={'max_stocks': 20})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        mem_before = get_memory_usage()
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=xlarge_dataset,
            start_date=xlarge_dataset.index[20],
            end_date=xlarge_dataset.index[-1],
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before

        assert result.is_success()

        n_trades = result.data['metrics']['n_trades']
        performance_metrics.record(
            '大规模测试_500股票_3年',
            500, 756, elapsed_time, mem_used, n_trades
        )

        print(f"\n大规模测试结果:")
        print(f"  股票数: 500")
        print(f"  天数: 756 (3年)")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  内存增量: {mem_used:.1f}MB")
        print(f"  交易次数: {n_trades}")
        print(f"  处理速度: {500/elapsed_time:.1f}股票/秒")

    @pytest.mark.slow
    def test_1000_stocks_1_year(self):
        """
        超大规模测试：1000股票 × 1年

        标记为slow，仅在完整测试时运行
        """
        prices = generate_price_data(1000, 252)

        engine = BacktestEngine(initial_capital=10000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 30})
        entry = ImmediateEntry(params={'max_stocks': 30})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        mem_before = get_memory_usage()
        start_time = time.time()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=prices,
            start_date=prices.index[20],
            end_date=prices.index[-1],
            rebalance_freq='W'
        )

        elapsed_time = time.time() - start_time
        mem_after = get_memory_usage()
        mem_used = mem_after - mem_before

        assert result.is_success()

        n_trades = result.data['metrics']['n_trades']
        performance_metrics.record(
            '超大规模测试_1000股票_1年',
            1000, 252, elapsed_time, mem_used, n_trades
        )

        print(f"\n超大规模测试结果:")
        print(f"  股票数: 1000")
        print(f"  天数: 252 (1年)")
        print(f"  耗时: {elapsed_time:.2f}秒")
        print(f"  内存增量: {mem_used:.1f}MB")
        print(f"  交易次数: {n_trades}")


class TestStrategyPerformanceComparison:
    """不同策略组合的性能对比"""

    def test_selector_performance_comparison(self, medium_dataset):
        """
        对比不同选股器的性��

        测试：Momentum vs Value vs External
        """
        selectors = [
            ('Momentum选股器', MomentumSelector(params={'lookback_period': 20, 'top_n': 10})),
            ('Value选股器', ValueSelector(params={'volatility_period': 20, 'return_period': 20, 'top_n': 10})),
            ('External选股器', ExternalSelector(params={'source': 'manual', 'manual_stocks': ','.join(medium_dataset.columns[:10])})),
        ]

        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        results = []

        for name, selector in selectors:
            engine = BacktestEngine(initial_capital=1000000)

            start_time = time.time()
            mem_before = get_memory_usage()

            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=medium_dataset,
                start_date=medium_dataset.index[20],
                end_date=medium_dataset.index[-1],
                rebalance_freq='W'
            )

            elapsed_time = time.time() - start_time
            mem_after = get_memory_usage()

            assert result.is_success()

            results.append({
                'name': name,
                'time': elapsed_time,
                'memory': mem_after - mem_before
            })

        print(f"\n选股器性能对比:")
        for r in results:
            print(f"  {r['name']}: {r['time']:.2f}秒, {r['memory']:.1f}MB")

    def test_entry_strategy_performance_comparison(self, medium_dataset):
        """
        对比不同入场策略的性能

        测试：Immediate vs MABreakout vs RSIOversold
        """
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})

        entries = [
            ('立即入场', ImmediateEntry(params={'max_stocks': 10})),
            ('均线突破', MABreakoutEntry(params={'short_window': 5, 'long_window': 20})),
            ('RSI超卖', RSIOversoldEntry(params={'rsi_period': 14, 'oversold_threshold': 30})),
        ]

        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        results = []

        for name, entry in entries:
            engine = BacktestEngine(initial_capital=1000000)

            start_time = time.time()

            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=medium_dataset,
                start_date=medium_dataset.index[20],
                end_date=medium_dataset.index[-1],
                rebalance_freq='W'
            )

            elapsed_time = time.time() - start_time

            assert result.is_success()

            results.append({
                'name': name,
                'time': elapsed_time
            })

        print(f"\n入场策略性能对比:")
        for r in results:
            print(f"  {r['name']}: {r['time']:.2f}秒")

    def test_exit_strategy_performance_comparison(self, medium_dataset):
        """
        对比不同退出策略的性能

        测试：Fixed vs ATR vs TimeBased vs Combined
        """
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})

        exits = [
            ('固定止损', FixedStopLossExit(params={'stop_loss_pct': -5.0})),
            ('ATR止损', ATRStopLossExit(params={'atr_period': 14, 'atr_multiplier': 2.0})),
            ('时间止损', TimeBasedExit(params={'holding_period': 10})),
        ]

        results = []

        for name, exit_strategy in exits:
            engine = BacktestEngine(initial_capital=1000000)

            start_time = time.time()

            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=medium_dataset,
                start_date=medium_dataset.index[20],
                end_date=medium_dataset.index[-1],
                rebalance_freq='W'
            )

            elapsed_time = time.time() - start_time

            assert result.is_success()

            results.append({
                'name': name,
                'time': elapsed_time
            })

        print(f"\n退出策略性能对比:")
        for r in results:
            print(f"  {r['name']}: {r['time']:.2f}秒")


class TestRebalanceFrequencyPerformance:
    """测试不同调仓频率的性能影响"""

    def test_rebalance_frequency_impact(self, medium_dataset):
        """
        对比不同调仓频率的性能影响

        测试：日频 vs 周频 vs 月频
        """
        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        frequencies = [
            ('日频', 'D'),
            ('周频', 'W'),
            ('月频', 'M'),
        ]

        results = []

        for name, freq in frequencies:
            start_time = time.time()

            result = engine.backtest_three_layer(
                selector=selector,
                entry=entry,
                exit_strategy=exit_strategy,
                prices=medium_dataset,
                start_date=medium_dataset.index[20],
                end_date=medium_dataset.index[-1],
                rebalance_freq=freq
            )

            elapsed_time = time.time() - start_time

            assert result.is_success()

            n_trades = result.data['metrics']['n_trades']

            results.append({
                'name': name,
                'time': elapsed_time,
                'trades': n_trades
            })

        print(f"\n调仓频率性能对比:")
        for r in results:
            print(f"  {r['name']}: {r['time']:.2f}秒, {r['trades']}笔交易")


class TestPerformanceBottleneck:
    """性能瓶颈分析"""

    def test_identify_bottleneck_components(self, medium_dataset):
        """
        识别性能瓶颈所在的组件

        分别测量：选股、入场判断、退出判断、回测引擎
        """
        import cProfile
        import pstats
        from io import StringIO

        engine = BacktestEngine(initial_capital=1000000)
        selector = MomentumSelector(params={'lookback_period': 20, 'top_n': 10})
        entry = ImmediateEntry(params={'max_stocks': 10})
        exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

        # 使用cProfile进行性能分析
        profiler = cProfile.Profile()
        profiler.enable()

        result = engine.backtest_three_layer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            prices=medium_dataset,
            start_date=medium_dataset.index[20],
            end_date=medium_dataset.index[-1],
            rebalance_freq='W'
        )

        profiler.disable()

        assert result.is_success()

        # 获取性能统计
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(20)  # 打印前20个最耗时的函数

        print(f"\n性能瓶颈分析（Top 20 函数）:")
        print(s.getvalue())


def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束时的钩子函数

    打印性能汇总报告
    """
    if hasattr(session.config, 'workerinput'):
        # 跳过worker进程
        return

    # 打印性能汇总
    performance_metrics.print_summary()


if __name__ == '__main__':
    # 运行性能测试
    pytest.main([__file__, '-v', '--tb=short', '-s'])
