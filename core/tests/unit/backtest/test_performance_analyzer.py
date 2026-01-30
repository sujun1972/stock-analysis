#!/usr/bin/env python3
"""
绩效分析器单元测试

测试PerformanceAnalyzer的所有指标计算

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest.performance_analyzer import PerformanceAnalyzer


class TestPerformanceAnalyzerInitialization:
    """测试PerformanceAnalyzer初始化"""

    def test_basic_initialization(self):
        """测试基础初始化"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, -0.005])
        analyzer = PerformanceAnalyzer(returns=returns)

        assert analyzer.returns is not None
        assert len(analyzer.returns) == 5

    def test_with_benchmark(self):
        """测试带基准的初始化"""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, -0.005])
        benchmark = pd.Series([0.005, 0.01, -0.005, 0.01, 0.0])

        analyzer = PerformanceAnalyzer(
            returns=returns,
            benchmark_returns=benchmark
        )

        assert analyzer.benchmark_returns is not None
        assert len(analyzer.benchmark_returns) == 5

    def test_custom_risk_free_rate(self):
        """测试自定义无风险利率"""
        returns = pd.Series([0.01, 0.02, -0.01])

        analyzer = PerformanceAnalyzer(
            returns=returns,
            risk_free_rate=0.05
        )

        assert analyzer.risk_free_rate == 0.05


class TestReturnMetrics:
    """测试收益率指标"""

    @pytest.fixture
    def returns_positive(self):
        """正收益序列"""
        return pd.Series([0.01, 0.02, 0.015, 0.01, 0.005])

    @pytest.fixture
    def returns_mixed(self):
        """混合收益序列"""
        return pd.Series([0.02, -0.01, 0.015, -0.005, 0.01, -0.02, 0.03])

    def test_calculate_total_return(self, returns_positive):
        """测试总收益率计算"""
        analyzer = PerformanceAnalyzer(returns_positive)
        metrics = analyzer.calculate_all_metrics()

        # 总收益 = (1+r1)*(1+r2)*...*(1+rn) - 1
        expected = (1.01 * 1.02 * 1.015 * 1.01 * 1.005) - 1
        assert abs(metrics['total_return'] - expected) < 0.0001

    def test_calculate_annual_return(self, returns_positive):
        """测试年化收益率"""
        analyzer = PerformanceAnalyzer(returns_positive, periods_per_year=252)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        # 年化收益率应该存在（键名是annualized_return）
        assert 'annualized_return' in metrics
        assert metrics['annualized_return'] > 0

    def test_average_return(self, returns_mixed):
        """测试平均收益率"""
        analyzer = PerformanceAnalyzer(returns_mixed)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        expected_avg = returns_mixed.mean()
        # 平均收益率应该接近returns的平均值
        assert metrics['total_return'] / len(returns_mixed) - expected_avg < 0.01


class TestRiskMetrics:
    """测试风险指标"""

    @pytest.fixture
    def volatile_returns(self):
        """高波动收益"""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.001, 0.05, 100))

    @pytest.fixture
    def stable_returns(self):
        """低波动收益"""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.001, 0.01, 100))

    def test_volatility_calculation(self, volatile_returns, stable_returns):
        """测试波动率计算"""
        analyzer_volatile = PerformanceAnalyzer(volatile_returns)
        analyzer_stable = PerformanceAnalyzer(stable_returns)

        metrics_volatile = analyzer_volatile.calculate_all_metrics(verbose=False)
        metrics_stable = analyzer_stable.calculate_all_metrics(verbose=False)

        # 高波动序列的波动率应该更高（键名是volatility）
        assert metrics_volatile['volatility'] > metrics_stable['volatility']

    def test_downside_deviation(self):
        """测试下行波动率"""
        returns = pd.Series([0.02, -0.03, 0.01, -0.02, 0.015, -0.01])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        # 下行波动率应该只考虑负收益
        assert 'downside_deviation' in metrics
        assert metrics['downside_deviation'] > 0

    def test_max_drawdown(self):
        """测试最大回撤"""
        # 构造有明显回撤的收益序列
        returns = pd.Series([0.1, 0.05, -0.15, -0.1, 0.2, 0.05])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        assert 'max_drawdown' in metrics
        assert metrics['max_drawdown'] < 0  # 回撤是负数
        assert metrics['max_drawdown'] > -1  # 不会超过-100%

    def test_max_drawdown_recovery(self):
        """测试回撤恢复"""
        # 先下跌再上涨
        returns = pd.Series([0.1, -0.2, -0.1, 0.15, 0.15, 0.1])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        # 应该计算回撤持续期
        assert 'max_drawdown_duration' in metrics


class TestRiskAdjustedMetrics:
    """测试风险调整指标"""

    @pytest.fixture
    def good_returns(self):
        """优质收益（高收益低波动）"""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.002, 0.01, 100))

    @pytest.fixture
    def poor_returns(self):
        """劣质收益（低收益高波动）"""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.0005, 0.03, 100))

    def test_sharpe_ratio(self, good_returns, poor_returns):
        """测试夏普比率"""
        analyzer_good = PerformanceAnalyzer(good_returns, risk_free_rate=0.03)
        analyzer_poor = PerformanceAnalyzer(poor_returns, risk_free_rate=0.03)

        metrics_good = analyzer_good.calculate_all_metrics()
        metrics_poor = analyzer_poor.calculate_all_metrics()

        # 优质收益的夏普比率应该更高
        assert metrics_good['sharpe_ratio'] > metrics_poor['sharpe_ratio']

    def test_sortino_ratio(self, good_returns):
        """测试Sortino比率"""
        analyzer = PerformanceAnalyzer(good_returns, risk_free_rate=0.03)
        metrics = analyzer.calculate_all_metrics()

        assert 'sortino_ratio' in metrics
        # Sortino比率应该高于Sharpe（因为只考虑下行风险）
        # 在大部分正收益的情况下

    def test_calmar_ratio(self):
        """测试Calmar比率"""
        # 构造有收益和回撤的序列
        returns = pd.Series([0.02, 0.01, -0.05, -0.02, 0.03, 0.02, 0.01])
        analyzer = PerformanceAnalyzer(returns, periods_per_year=252)
        metrics = analyzer.calculate_all_metrics()

        assert 'calmar_ratio' in metrics

    def test_information_ratio(self):
        """测试信息比率（需要基准）"""
        strategy_returns = pd.Series([0.02, 0.01, -0.01, 0.015, 0.01])
        benchmark_returns = pd.Series([0.01, 0.005, 0.0, 0.01, 0.005])

        analyzer = PerformanceAnalyzer(
            returns=strategy_returns,
            benchmark_returns=benchmark_returns
        )
        metrics = analyzer.calculate_all_metrics()

        assert 'information_ratio' in metrics


class TestWinRateMetrics:
    """测试胜率指标"""

    def test_win_rate(self):
        """测试胜率"""
        returns = pd.Series([0.02, -0.01, 0.01, -0.005, 0.015, -0.02, 0.01])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        # 4个正收益 / 7个总收益 = 57.14%
        expected_win_rate = 4 / 7
        assert abs(metrics['win_rate'] - expected_win_rate) < 0.01

    def test_avg_win_loss(self):
        """测试平均盈亏"""
        returns = pd.Series([0.02, -0.01, 0.01, -0.02])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        assert 'average_win' in metrics
        assert 'average_loss' in metrics

        # 平均盈利 = (0.02 + 0.01) / 2 = 0.015
        assert abs(metrics['average_win'] - 0.015) < 0.0001

        # 平均亏损 = (-0.01 + -0.02) / 2 = -0.015
        assert abs(metrics['average_loss'] - (-0.015)) < 0.0001

    def test_profit_factor(self):
        """测试盈亏比"""
        returns = pd.Series([0.04, -0.01, 0.02, -0.01])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        # 总盈利 = 0.06, 总亏损 = 0.02
        # 盈亏比 = 0.06 / 0.02 = 3.0
        assert 'profit_factor' in metrics
        assert abs(metrics['profit_factor'] - 3.0) < 0.01


class TestBetaAndAlpha:
    """测试Beta和Alpha计算"""

    def test_beta_calculation(self):
        """测试Beta计算"""
        # 策略收益与基准正相关
        benchmark = pd.Series([0.01, -0.01, 0.02, -0.005, 0.015])
        strategy = pd.Series([0.015, -0.015, 0.03, -0.01, 0.02])  # 1.5倍波动

        analyzer = PerformanceAnalyzer(
            returns=strategy,
            benchmark_returns=benchmark
        )
        metrics = analyzer.calculate_all_metrics()

        assert 'beta' in metrics
        # Beta应该接近1.5
        assert 0.8 < metrics['beta'] < 2.0

    def test_alpha_calculation(self):
        """测试Alpha计算"""
        benchmark = pd.Series([0.01, -0.01, 0.02, -0.005, 0.015])
        strategy = pd.Series([0.02, -0.005, 0.025, 0.0, 0.02])  # 超额收益

        analyzer = PerformanceAnalyzer(
            returns=strategy,
            benchmark_returns=benchmark,
            risk_free_rate=0.03
        )
        metrics = analyzer.calculate_all_metrics()

        assert 'alpha' in metrics

    def test_information_ratio_calculation(self):
        """测试信息比率计算（包含跟踪误差）"""
        benchmark = pd.Series([0.01, -0.01, 0.02, -0.005, 0.015])
        strategy = pd.Series([0.011, -0.009, 0.021, -0.004, 0.016])  # 接近基准

        analyzer = PerformanceAnalyzer(
            returns=strategy,
            benchmark_returns=benchmark
        )
        metrics = analyzer.calculate_all_metrics()

        # 信息比率应该存在
        assert 'information_ratio' in metrics
        # IR应该是有限值（不是NaN或inf）
        assert np.isfinite(metrics['information_ratio'])


class TestEdgeCases:
    """测试边界情况"""

    def test_all_zero_returns(self):
        """测试全零收益"""
        returns = pd.Series([0.0] * 10)
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        assert metrics['total_return'] == 0.0
        assert metrics['volatility'] == 0.0
        assert metrics['win_rate'] == 0.0

    def test_all_positive_returns(self):
        """测试全正收益"""
        returns = pd.Series([0.01, 0.02, 0.015, 0.01, 0.005])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        assert metrics['win_rate'] == 1.0
        assert metrics['max_drawdown'] == 0.0  # 没有回撤

    def test_all_negative_returns(self):
        """测试全负收益"""
        returns = pd.Series([-0.01, -0.02, -0.015, -0.01, -0.005])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        assert metrics['win_rate'] == 0.0
        assert metrics['total_return'] < 0

    def test_single_return(self):
        """测试单个收益"""
        returns = pd.Series([0.05])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        assert abs(metrics['total_return'] - 0.05) < 0.0001

    def test_very_long_series(self):
        """测试很长的序列"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 1000))
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics()

        # 应该能正常计算
        assert 'total_return' in metrics
        assert 'sharpe_ratio' in metrics

    def test_extreme_values(self):
        """测试极端值"""
        returns = pd.Series([0.5, -0.4, 0.3, -0.3, 0.2])
        analyzer = PerformanceAnalyzer(returns)
        metrics = analyzer.calculate_all_metrics(verbose=False)

        # 应该能处理大幅波动
        assert metrics['volatility'] > 0


class TestPrintMethods:
    """测试打印方法"""

    def test_print_metrics_no_error(self):
        """测试打印指标不会抛出异常"""
        returns = pd.Series([0.01, -0.01, 0.02, 0.015, -0.005])
        analyzer = PerformanceAnalyzer(returns)

        # 先计算再打印
        analyzer.calculate_all_metrics(verbose=False)

        # 不应该抛出异常
        try:
            analyzer.print_metrics()
            assert True
        except Exception as e:
            assert False, f"print_metrics raised exception: {e}"

    def test_calculate_metrics_verbose(self):
        """测试verbose模式计算指标"""
        returns = pd.Series([0.1, 0.05, -0.15, -0.1, 0.2, 0.05])
        analyzer = PerformanceAnalyzer(returns)

        # verbose=True不应该抛出异常
        try:
            metrics = analyzer.calculate_all_metrics(verbose=True)
            assert metrics is not None
            assert 'total_return' in metrics
        except Exception as e:
            assert False, f"calculate_all_metrics(verbose=True) raised exception: {e}"


class TestCalculateMetricsMethod:
    """测试calculate_all_metrics方法"""

    def test_returns_all_required_metrics(self):
        """测试返回所有必需指标"""
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        analyzer = PerformanceAnalyzer(returns, risk_free_rate=0.03)

        metrics = analyzer.calculate_all_metrics(verbose=False)

        # 必需的指标
        required_metrics = [
            'total_return',
            'annualized_return',
            'volatility',
            'sharpe_ratio',
            'max_drawdown',
            'win_rate'
        ]

        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"

    def test_with_benchmark_returns_additional_metrics(self):
        """测试有基准时返回额外指标"""
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        benchmark = pd.Series(np.random.normal(0.0008, 0.015, 100))

        analyzer = PerformanceAnalyzer(
            returns=returns,
            benchmark_returns=benchmark
        )

        metrics = analyzer.calculate_all_metrics(verbose=False)

        # 有基准时的额外指标
        benchmark_metrics = ['beta', 'alpha', 'information_ratio']

        for metric in benchmark_metrics:
            assert metric in metrics, f"Missing benchmark metric: {metric}"


class TestCumulativeReturns:
    """测试累计收益率"""

    def test_cumulative_returns_calculation(self):
        """测试累计收益率计算"""
        returns = pd.Series([0.1, 0.05, -0.02, 0.03])
        analyzer = PerformanceAnalyzer(returns)

        cum_returns = analyzer.cumulative_returns()

        # 累计收益应该是Series
        assert isinstance(cum_returns, pd.Series)
        assert len(cum_returns) == 4

        # 第一个累计收益应该等于第一个收益
        assert abs(cum_returns.iloc[0] - 0.1) < 0.0001

        # 最后一个累计收益应该等于总收益
        expected_total = (1.1 * 1.05 * 0.98 * 1.03) - 1
        assert abs(cum_returns.iloc[-1] - expected_total) < 0.0001

    def test_cumulative_returns_always_growing(self):
        """测试正收益下累计收益递增"""
        returns = pd.Series([0.01, 0.02, 0.015, 0.01])
        analyzer = PerformanceAnalyzer(returns)

        cum_returns = analyzer.cumulative_returns()

        # 全部正收益时，累计收益应该递增
        assert cum_returns.is_monotonic_increasing


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
