#!/usr/bin/env python3
"""
特征计算性能基准测试

测试目标（基于REFACTORING_PLAN.md任务1.2.2）:
- 125个Alpha因子计算: <60秒 (1000股×250天)
- 60+技术指标计算: <30秒
- 单因子平均计算: <0.5秒

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

from features.alpha_factors import (
    AlphaFactors,
    MomentumFactorCalculator,
    ReversalFactorCalculator,
    VolatilityFactorCalculator,
    VolumeFactorCalculator,
)
from features.technical_indicators import TechnicalIndicators
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
    从 Response 对象中提取数据

    在重构过程中，Alpha 因子计算函数从直接返回 DataFrame 改为返回 Response 对象。
    此函数用于统一解包 Response 对象，提取其中的 DataFrame。

    Args:
        response: Response 对象或原始数据（兼容旧 API）

    Returns:
        pd.DataFrame: 解包后的 DataFrame，包含计算后的特征

    Raises:
        ValueError: 如果 Response 状态为失败

    Examples:
        >>> alpha = AlphaFactors(data)
        >>> result = unwrap_response(alpha.add_all_alpha_factors())
        >>> assert isinstance(result, pd.DataFrame)
    """
    if isinstance(response, Response):
        if not response.is_success():
            raise ValueError(f"操作失败: {response.error_message}")
        return response.data
    return response


# ==================== Alpha因子性能测试 ====================


class TestAlphaFactorsPerformance(PerformanceBenchmarkBase):
    """Alpha因子计算性能测试"""

    def test_all_alpha_factors_benchmark(self, single_stock_data_long):
        """
        测试所有125+Alpha因子计算性能

        数据规模: 1只股票×1000天
        性能目标: 单股票计算应该非常快,为大规模测试做准备
        """
        print_benchmark_header("Alpha因子计算性能测试 - 所有因子")

        data = single_stock_data_long.copy()

        # 执行计算
        start = time.time()
        alpha = AlphaFactors(data)
        result_response = alpha.add_all_alpha_factors()
        result = unwrap_response(result_response)  # 解包Response对象
        elapsed = time.time() - start

        # 验证结果
        assert len(result) == len(data)
        assert len(result.columns) >= 20  # 至少20个Alpha因子

        # 性能断言（单股票应该很快）
        threshold = 5.0  # 单股票5秒内完成
        print_benchmark_result(
            f"所有Alpha因子计算 (1股×{len(data)}天, {len(result.columns)}个因子)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="所有Alpha因子(单股票)",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_days': len(data), 'n_factors': len(result.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "所有Alpha因子计算(单股票)",
            {'n_days': len(data), 'n_factors': len(result.columns)}
        )

    def test_momentum_factors_benchmark(self, single_stock_data_long):
        """测试动量因子计算性能"""
        print_benchmark_header("动量因子计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        calc = MomentumFactorCalculator(data)
        result_response = calc.calculate_all()
        result = unwrap_response(result_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = 0.5  # 单因子类型<0.5秒
        print_benchmark_result(
            f"动量因子计算 ({len(result.columns)}个因子)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="动量因子",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_factors': len(result.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "动量因子计算",
            {'n_factors': len(result.columns)}
        )

    def test_reversal_factors_benchmark(self, single_stock_data_long):
        """测试反转因子计算性能"""
        print_benchmark_header("反转因子计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        calc = ReversalFactorCalculator(data)
        result_response = calc.calculate_all()
        result = unwrap_response(result_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = 0.5
        print_benchmark_result(
            f"反转因子计算 ({len(result.columns)}个因子)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="反转因子",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_factors': len(result.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "反转因子计算",
            {'n_factors': len(result.columns)}
        )

    def test_volatility_factors_benchmark(self, single_stock_data_long):
        """测试波动率因子计算性能"""
        print_benchmark_header("波动率因子计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        calc = VolatilityFactorCalculator(data)
        result_response = calc.calculate_all()
        result = unwrap_response(result_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = 0.5
        print_benchmark_result(
            f"波动率因子计算 ({len(result.columns)}个因子)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="波动率因子",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_factors': len(result.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "波动率因子计算",
            {'n_factors': len(result.columns)}
        )

    def test_volume_factors_benchmark(self, single_stock_data_long):
        """测试成交量因子计算性能"""
        print_benchmark_header("成交量因子计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        calc = VolumeFactorCalculator(data)
        result_response = calc.calculate_all()
        result = unwrap_response(result_response)  # 解包Response对象
        elapsed = time.time() - start

        threshold = 0.5
        print_benchmark_result(
            f"成交量因子计算 ({len(result.columns)}个因子)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="成交量因子",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_factors': len(result.columns)}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "成交量因子计算",
            {'n_factors': len(result.columns)}
        )


# ==================== 技术指标性能测试 ====================


class TestTechnicalIndicatorsPerformance(PerformanceBenchmarkBase):
    """技术指标计算性能测试"""

    def test_all_technical_indicators_benchmark(self, single_stock_data_long):
        """
        测试所有60+技术指标计算性能

        性能目标: <30秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("技术指标计算性能测试 - 所有指标")

        data = single_stock_data_long.copy()

        start = time.time()
        tech = TechnicalIndicators(data)
        result = tech.add_all_indicators()
        elapsed = time.time() - start

        # 验证结果
        assert len(result) == len(data)
        n_indicators = len([col for col in result.columns if col not in data.columns])
        assert n_indicators >= 10  # 至少10���技术指标

        # 性能断言（单股票应该很快）
        threshold = 3.0  # 单股票3秒内完成
        print_benchmark_result(
            f"所有技术指标计算 (1股×{len(data)}天, {n_indicators}个指标)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name="所有技术指标(单股票)",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_days': len(data), 'n_indicators': n_indicators}
        )

        self.assert_performance(
            elapsed,
            threshold,
            "所有技术指标计算(单股票)",
            {'n_days': len(data), 'n_indicators': n_indicators}
        )

    def test_moving_averages_benchmark(self, single_stock_data_long):
        """测试移动平均线计算性能"""
        print_benchmark_header("移动平均线计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        tech = TechnicalIndicators(data)
        result = tech.add_moving_averages()
        elapsed = time.time() - start

        threshold = 0.3
        print_benchmark_result("移动平均线计算", elapsed, threshold)

        performance_reporter.add_result(
            category="特征计算",
            test_name="移动平均线",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "移动平均线计算")

    def test_rsi_benchmark(self, single_stock_data_long):
        """测试RSI计算性能"""
        print_benchmark_header("RSI计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        tech = TechnicalIndicators(data)
        result = tech.add_rsi()
        elapsed = time.time() - start

        threshold = 0.2
        print_benchmark_result("RSI计算", elapsed, threshold)

        performance_reporter.add_result(
            category="特征计算",
            test_name="RSI指标",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "RSI计算")

    def test_macd_benchmark(self, single_stock_data_long):
        """测试MACD计算性能"""
        print_benchmark_header("MACD计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        tech = TechnicalIndicators(data)
        result = tech.add_macd()
        elapsed = time.time() - start

        threshold = 0.2
        print_benchmark_result("MACD计算", elapsed, threshold)

        performance_reporter.add_result(
            category="特征计算",
            test_name="MACD指标",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "MACD计算")

    def test_bollinger_bands_benchmark(self, single_stock_data_long):
        """测试布林带计算性能"""
        print_benchmark_header("布林带计算性能测试")

        data = single_stock_data_long.copy()

        start = time.time()
        tech = TechnicalIndicators(data)
        result = tech.add_bollinger_bands()
        elapsed = time.time() - start

        threshold = 0.3
        print_benchmark_result("布林带计算", elapsed, threshold)

        performance_reporter.add_result(
            category="特征计算",
            test_name="布林带指标",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold
        )

        self.assert_performance(elapsed, threshold, "布林带计算")


# ==================== 批量计算性能测试 ====================


class TestBatchCalculationPerformance(PerformanceBenchmarkBase):
    """批量计算性能测试（模拟多股票场景）"""

    def test_batch_alpha_calculation_10_stocks(self, single_stock_data_long):
        """测试10只股票批量Alpha因子计算"""
        print_benchmark_header("批量Alpha因子计算 - 10只股票")

        # 模拟10只股票
        n_stocks = 10
        data = single_stock_data_long.copy()

        start = time.time()
        results = []
        for i in range(n_stocks):
            alpha = AlphaFactors(data)
            result_response = alpha.add_all_alpha_factors()
            result = unwrap_response(result_response)  # 解包Response对象
            results.append(result)
        elapsed = time.time() - start

        threshold = 50.0  # 10只股票50秒内完成
        print_benchmark_result(
            f"批量Alpha因子计算 ({n_stocks}只股票)",
            elapsed,
            threshold
        )

        performance_reporter.add_result(
            category="特征计算",
            test_name=f"批量Alpha因子({n_stocks}只股票)",
            elapsed=elapsed,
            threshold=threshold,
            passed=elapsed < threshold,
            details={'n_stocks': n_stocks}
        )

        self.assert_performance(
            elapsed,
            threshold,
            f"批量Alpha因子计算({n_stocks}只股票)",
            {'n_stocks': n_stocks}
        )

    def test_single_factor_average_time(self, single_stock_data):
        """
        测试单因子平均计算时间

        性能目标: <0.5秒 (基于REFACTORING_PLAN.md)
        """
        print_benchmark_header("单因子平均计算时间测试")

        data = single_stock_data.copy()

        # 测试多个单因子
        single_factor_times = []

        # 动量因子
        start = time.time()
        calc = MomentumFactorCalculator(data)
        result = calc.add_momentum_factors(periods=[20])
        single_factor_times.append(time.time() - start)

        # 反转因子
        start = time.time()
        calc = ReversalFactorCalculator(data)
        result = calc.add_reversal_factors(short_periods=[5], long_periods=[])
        single_factor_times.append(time.time() - start)

        # 波动率因子
        start = time.time()
        calc = VolatilityFactorCalculator(data)
        result = calc.add_volatility_factors(periods=[20])
        single_factor_times.append(time.time() - start)

        # 计算平均时间
        avg_time = np.mean(single_factor_times)
        max_time = np.max(single_factor_times)

        threshold = PerformanceThresholds.SINGLE_FACTOR_AVG
        print_benchmark_result(
            f"单因子平均计算时间 (测试{len(single_factor_times)}个因子)",
            avg_time,
            threshold
        )
        print(f"  最慢因子: {max_time:.3f}s")

        performance_reporter.add_result(
            category="特征计算",
            test_name="单因子平均计算时间",
            elapsed=avg_time,
            threshold=threshold,
            passed=avg_time < threshold,
            details={'n_tests': len(single_factor_times), 'max_time': max_time}
        )

        self.assert_performance(
            avg_time,
            threshold,
            "单因子平均计算时间",
            {'avg': avg_time, 'max': max_time}
        )


# ==================== 内存和优化测试 ====================


class TestMemoryAndOptimization(PerformanceBenchmarkBase):
    """内存使用和优化效果测试"""

    def test_vectorized_vs_loop_performance(self, single_stock_data):
        """测试向量化vs循环的性能差异"""
        print_benchmark_header("向量化性能提升测试")

        data = single_stock_data.copy()

        # 向量化计算
        start = time.time()
        vectorized_result = data['close'].pct_change(20)
        vectorized_time = time.time() - start

        # 循环计算（慢速版本）
        start = time.time()
        loop_result = pd.Series(index=data.index, dtype=float)
        for i in range(20, len(data)):
            loop_result.iloc[i] = (data['close'].iloc[i] / data['close'].iloc[i-20]) - 1
        loop_time = time.time() - start

        speedup = loop_time / vectorized_time if vectorized_time > 0 else float('inf')

        print(f"  向量化: {vectorized_time:.4f}s")
        print(f"  循环:   {loop_time:.4f}s")
        print(f"  加速比: {speedup:.1f}x")

        # 验证结果一致性（允许小误差）
        assert np.allclose(
            vectorized_result.dropna(),
            loop_result.dropna(),
            rtol=1e-10,
            atol=1e-10
        ), "向量化和循环结果不一致"

        # 向量化应该至少快5倍
        assert speedup > 5.0, f"向量化加速不足: {speedup:.1f}x < 5x"

        performance_reporter.add_result(
            category="优化效果",
            test_name="向量化加速比",
            elapsed=vectorized_time,
            threshold=loop_time / 5.0,
            passed=speedup > 5.0,
            details={'speedup': f"{speedup:.1f}x"}
        )


if __name__ == '__main__':
    # 运行性能测试
    pytest.main([__file__, '-v', '--tb=short'])
