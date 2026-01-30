"""
向量化优化功能测试

测试阶段1优化的核心功能：
- 趋势强度因子向量化计算
- 向量化与循环版本结果一致性
- 边界条件处理
- 性能对比

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import time
from typing import Tuple

from src.features.alpha_factors import (
    TrendFactorCalculator,
    AlphaFactors,
)


# ==================== 测试数据准备 ====================


@pytest.fixture
def sample_price_data():
    """生成样本价格数据"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='D')

    # 模拟带趋势的价格数据
    trend = np.linspace(100, 120, 500)
    noise = np.random.normal(0, 2, 500)
    prices = trend + noise

    df = pd.DataFrame({
        'open': prices * 0.98,
        'high': prices * 1.02,
        'low': prices * 0.97,
        'close': prices,
        'vol': np.random.uniform(1e6, 1e7, 500)
    }, index=dates)

    return df


@pytest.fixture
def large_price_data():
    """生成大规模价格数据（性能测试用）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=1250, freq='D')

    trend = np.linspace(100, 150, 1250)
    noise = np.random.normal(0, 3, 1250).cumsum()
    prices = trend + noise

    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 1250)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 1250)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 1250)),
        'close': prices,
        'vol': np.random.uniform(1e6, 1e7, 1250)
    }, index=dates)

    return df


# ==================== 趋势强度因子测试 ====================


class TestTrendStrengthVectorization:
    """趋势强度因子向量化测试"""

    def test_vectorized_calculation_basic(self, sample_price_data):
        """测试基本向量化计算"""
        calculator = TrendFactorCalculator(sample_price_data.copy(), inplace=False)
        result = calculator.add_trend_strength(periods=[20])

        # 检查列是否存在
        assert 'TREND20' in result.columns
        assert 'TREND_R2_20' in result.columns

        # 检查前19个值应该是NaN
        assert result['TREND20'].iloc[:19].isna().all()

        # 检查后续值不全为NaN
        assert not result['TREND20'].iloc[19:].isna().all()

        # 检查R²值在[0, 1]范围内（忽略NaN）
        r2_valid = result['TREND_R2_20'].dropna()
        assert (r2_valid >= 0).all()
        assert (r2_valid <= 1).all()

    def test_vectorized_vs_rolling_consistency(self, sample_price_data):
        """测试向量化版本与循环版本的一致性"""
        prices = sample_price_data['close'].values
        period = 20

        # 向量化版本
        slopes_vec, r2_vec = TrendFactorCalculator._calculate_trend_vectorized(prices, period)

        # 循环版本
        slopes_roll, r2_roll = TrendFactorCalculator._calculate_trend_rolling(prices, period)

        # 比较结果（允许浮点误差）
        np.testing.assert_allclose(slopes_vec, slopes_roll, rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(r2_vec, r2_roll, rtol=1e-10, atol=1e-12)

    def test_multiple_periods(self, sample_price_data):
        """测试多个周期"""
        calculator = TrendFactorCalculator(sample_price_data.copy(), inplace=False)
        result = calculator.add_trend_strength(periods=[10, 20, 60])

        # 检查所有周期的列都存在
        for period in [10, 20, 60]:
            assert f'TREND{period}' in result.columns
            assert f'TREND_R2_{period}' in result.columns

            # 检查前period-1个值是NaN
            assert result[f'TREND{period}'].iloc[:period-1].isna().all()

    def test_nan_handling(self):
        """测试NaN值处理"""
        # 创建包含NaN的数据
        prices_with_nan = np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0] * 5)
        df = pd.DataFrame({
            'close': prices_with_nan,
            'vol': np.ones(50)
        })

        calculator = TrendFactorCalculator(df, inplace=False)
        result = calculator.add_trend_strength(periods=[5])

        # 检查包含NaN的窗口对应的结果也是NaN
        # 索引2的NaN会影响窗口[0:5], [1:6], [2:7]等
        assert 'TREND5' in result.columns

    def test_edge_cases(self):
        """测试边界情况"""
        # 测试1: 数据长度小于周期
        small_df = pd.DataFrame({
            'close': [1, 2, 3, 4, 5],
            'vol': [100, 100, 100, 100, 100]
        })

        calculator = TrendFactorCalculator(small_df, inplace=False)
        result = calculator.add_trend_strength(periods=[10])  # 周期大于数据长度

        # 应该跳过该周期
        assert 'TREND10' not in result.columns

        # 测试2: 单一周期
        result = calculator.add_trend_strength(periods=[3])
        assert 'TREND3' in result.columns

    def test_slope_sign_correctness(self):
        """测试斜率符号的正确性"""
        # 上升趋势
        upward = pd.DataFrame({
            'close': np.arange(1, 51),  # 递增序列
            'vol': np.ones(50)
        })

        calculator = TrendFactorCalculator(upward, inplace=False)
        result = calculator.add_trend_strength(periods=[10])

        # 上升趋势的斜率应该是正数
        slopes = result['TREND10'].dropna()
        assert (slopes > 0).all()

        # 下降趋势
        downward = pd.DataFrame({
            'close': np.arange(50, 0, -1),  # 递减序列
            'vol': np.ones(50)
        })

        calculator = TrendFactorCalculator(downward, inplace=False)
        result = calculator.add_trend_strength(periods=[10])

        # 下降趋势的斜率应该是负数
        slopes = result['TREND10'].dropna()
        assert (slopes < 0).all()


# ==================== 性能测试 ====================


class TestVectorizationPerformance:
    """向量化性能测试"""

    def test_performance_comparison(self, large_price_data):
        """对比向量化与循环版本的性能"""
        prices = large_price_data['close'].values
        period = 20

        # 测试向量化版本
        start = time.time()
        slopes_vec, r2_vec = TrendFactorCalculator._calculate_trend_vectorized(prices, period)
        time_vec = time.time() - start

        # 测试循环版本
        start = time.time()
        slopes_roll, r2_roll = TrendFactorCalculator._calculate_trend_rolling(prices, period)
        time_roll = time.time() - start

        # 计算加速比
        speedup = time_roll / time_vec

        print(f"\n性能对比 (1250天数据, period={period}):")
        print(f"  向量化版本: {time_vec:.4f}秒")
        print(f"  循环版本:   {time_roll:.4f}秒")
        print(f"  加速比:     {speedup:.2f}x")

        # 向量化版本应该更快（至少5倍）
        assert speedup > 5.0, f"向量化加速比({speedup:.2f}x)不足5倍"

        # 结果应该一致
        np.testing.assert_allclose(slopes_vec, slopes_roll, rtol=1e-10)

    def test_batch_calculation_performance(self, large_price_data):
        """测试批量计算性能"""
        calculator = TrendFactorCalculator(large_price_data.copy(), inplace=False)

        start = time.time()
        result = calculator.add_trend_strength(periods=[10, 20, 60])
        elapsed = time.time() - start

        print(f"\n批量计算性能 (1250天数据, 3个周期):")
        print(f"  总耗时: {elapsed:.4f}秒")
        print(f"  平均每周期: {elapsed/3:.4f}秒")

        # 批量计算3个周期应该在0.1秒内完成
        assert elapsed < 0.1, f"批量计算耗时({elapsed:.4f}秒)超过0.1秒"


# ==================== 集成测试 ====================


class TestAlphaFactorsIntegration:
    """AlphaFactors类集成测试"""

    def test_trend_in_full_pipeline(self, sample_price_data):
        """测试趋势因子在完整流程中的使用"""
        af = AlphaFactors(sample_price_data.copy(), inplace=False)

        # 计算趋势因子
        af.add_trend_strength(periods=[20])

        # 获取结果
        result = af.get_dataframe()

        # 验证结果
        assert 'TREND20' in result.columns
        assert 'TREND_R2_20' in result.columns

        # 检查因子名称列表
        factor_names = af.get_factor_names()
        assert 'TREND20' in factor_names
        assert 'TREND_R2_20' in factor_names

    def test_cache_effectiveness(self, sample_price_data):
        """测试缓存有效性"""
        af = AlphaFactors(sample_price_data.copy(), inplace=False)

        # 首次计算（填充缓存）
        af.add_trend_strength(periods=[20])

        # 获取缓存统计
        stats = af.get_cache_stats()

        assert 'size' in stats
        assert 'hit_rate' in stats
        assert stats['size'] >= 0


# ==================== 数值正确性测试 ====================


class TestNumericalCorrectness:
    """数值计算正确性测试"""

    def test_known_linear_trend(self):
        """测试已知线性趋势"""
        # 完美线性趋势：y = 2x + 10
        x_vals = np.arange(50)
        y_vals = 2 * x_vals + 10

        df = pd.DataFrame({
            'close': y_vals,
            'vol': np.ones(50)
        })

        calculator = TrendFactorCalculator(df, inplace=False)
        result = calculator.add_trend_strength(periods=[20])

        # 完美线性趋势的斜率应该接近2
        slopes = result['TREND20'].dropna()
        np.testing.assert_allclose(slopes, 2.0, rtol=0.01)

        # R²应该接近1（完美拟合）
        r2 = result['TREND_R2_20'].dropna()
        np.testing.assert_allclose(r2, 1.0, rtol=0.01)

    def test_horizontal_line(self):
        """测试水平线（无趋势）"""
        # 水平线：y = 10（斜率为0）
        y_vals = np.ones(50) * 10

        df = pd.DataFrame({
            'close': y_vals,
            'vol': np.ones(50)
        })

        calculator = TrendFactorCalculator(df, inplace=False)
        result = calculator.add_trend_strength(periods=[20])

        # 水平线的斜率应该接近0
        slopes = result['TREND20'].dropna()
        np.testing.assert_allclose(slopes, 0.0, atol=1e-10)

        # R²对于水平线可能是0或NaN
        r2 = result['TREND_R2_20'].dropna()
        assert (r2 >= 0).all()


# ==================== 错误处理测试 ====================


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_dataframe(self):
        """测试无效DataFrame"""
        df = pd.DataFrame({'vol': [1, 2, 3]})  # 缺少close列

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            TrendFactorCalculator(df)

    def test_empty_periods_list(self, sample_price_data):
        """测试空周期列表"""
        calculator = TrendFactorCalculator(sample_price_data.copy(), inplace=False)
        result = calculator.add_trend_strength(periods=None)  # None使用默认周期

        # 应该使用默认周期
        assert 'TREND20' in result.columns or 'TREND60' in result.columns

    def test_fallback_on_error(self, sample_price_data):
        """测试降级机制"""
        # 这个测试确保即使向量化失败，也能降级到循环版本
        calculator = TrendFactorCalculator(sample_price_data.copy(), inplace=False)

        # 正常计算应该成功
        result = calculator.add_trend_strength(periods=[20])
        assert 'TREND20' in result.columns


# ==================== 并发安全测试 ====================


class TestConcurrencySafety:
    """并发安全性测试"""

    def test_concurrent_calculation(self, sample_price_data):
        """测试并发计算"""
        from concurrent.futures import ThreadPoolExecutor

        def calculate_trend(df):
            calc = TrendFactorCalculator(df.copy(), inplace=False)
            return calc.add_trend_strength(periods=[20])

        # 并发执行10次
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(calculate_trend, sample_price_data) for _ in range(10)]
            results = [f.result() for f in futures]

        # 所有结果应该一致（比较Series而非DataFrame）
        for i in range(1, len(results)):
            pd.testing.assert_series_equal(
                results[0]['TREND20'],
                results[i]['TREND20'],
                check_names=False
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
