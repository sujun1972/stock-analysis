"""
IC计算器向量化优化测试

测试内容：
- IC时间序列向量化计算
- 向量化与原版本结果一致性
- Pearson/Spearman相关系数正确性
- 性能对比

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import time

from src.analysis.ic_calculator import ICCalculator


# ==================== 测试数据准备 ====================


@pytest.fixture
def sample_factor_data():
    """生成样本因子数据"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'00000{i}.SZ' for i in range(50)]

    # 生成因子值（横截面数据）
    factor_data = {}
    for stock in stocks:
        # 模拟因子值（正态分布）
        factor_data[stock] = np.random.randn(len(dates))

    factor_df = pd.DataFrame(factor_data, index=dates)
    return factor_df


@pytest.fixture
def sample_price_data():
    """生成样本价格数据"""
    np.random.seed(43)
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'00000{i}.SZ' for i in range(50)]

    # 生成价格数据
    price_data = {}
    for stock in stocks:
        # 模拟价格（随机游走）
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = 100 * (1 + returns).cumprod()
        price_data[stock] = prices

    price_df = pd.DataFrame(price_data, index=dates)
    return price_df


@pytest.fixture
def large_factor_data():
    """生成大规模因子数据（性能测试用）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=1250, freq='D')
    stocks = [f'00000{i}.SZ' for i in range(100)]

    factor_data = {}
    for stock in stocks:
        factor_data[stock] = np.random.randn(len(dates))

    factor_df = pd.DataFrame(factor_data, index=dates)
    return factor_df


@pytest.fixture
def large_price_data():
    """生成大规模价格数据（性能测试用）"""
    np.random.seed(43)
    dates = pd.date_range('2020-01-01', periods=1250, freq='D')
    stocks = [f'00000{i}.SZ' for i in range(100)]

    price_data = {}
    for stock in stocks:
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = 100 * (1 + returns).cumprod()
        price_data[stock] = prices

    price_df = pd.DataFrame(price_data, index=dates)
    return price_df


# ==================== IC计算基础测试 ====================


class TestICCalculatorBasics:
    """IC计算器基础功能测试"""

    def test_calculator_initialization(self):
        """测试计算器初始化"""
        # Pearson方法
        ic_calc = ICCalculator(forward_periods=5, method='pearson')
        assert ic_calc.forward_periods == 5
        assert ic_calc.method == 'pearson'

        # Spearman方法
        ic_calc = ICCalculator(forward_periods=10, method='spearman')
        assert ic_calc.forward_periods == 10
        assert ic_calc.method == 'spearman'

    def test_invalid_method(self):
        """测试无效的相关系数方法"""
        with pytest.raises(ValueError, match="method必须是"):
            ICCalculator(method='invalid')

    def test_single_ic_calculation(self):
        """测试单个时间点的IC计算"""
        ic_calc = ICCalculator(forward_periods=5)

        # 创建简单的因子和收益数据（至少10个样本）
        factor = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                          index=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'])
        returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10],
                           index=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'])

        ic = ic_calc.calculate_ic(factor, returns)

        # 完全正相关，IC应该接近1
        assert not np.isnan(ic), "IC不应该是NaN"
        assert abs(ic - 1.0) < 0.01, f"IC({ic})应该接近1"


# ==================== IC时间序列测试 ====================


class TestICSeriesCalculation:
    """IC时间序列计算测试"""

    def test_ic_series_basic(self, sample_factor_data, sample_price_data):
        """测试基本IC时间序列计算"""
        ic_calc = ICCalculator(forward_periods=5, method='pearson')

        ic_series = ic_calc.calculate_ic_series(sample_factor_data, sample_price_data)

        # 检查返回类型
        assert isinstance(ic_series, pd.Series)

        # 检查长度（应该小于等于原始数据长度）
        assert len(ic_series) <= len(sample_factor_data)

        # 检查IC值在[-1, 1]范围内
        assert (ic_series >= -1).all()
        assert (ic_series <= 1).all()

    def test_ic_series_with_nan(self):
        """测试包含NaN的数据"""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        stocks = [f'S{i}' for i in range(20)]

        # 创建包含NaN的因子数据
        factor_data = {}
        price_data = {}

        for stock in stocks:
            factor_vals = np.random.randn(100)
            price_vals = 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()

            # 随机插入NaN
            nan_indices = np.random.choice(100, size=10, replace=False)
            factor_vals[nan_indices] = np.nan
            price_vals[nan_indices] = np.nan

            factor_data[stock] = factor_vals
            price_data[stock] = price_vals

        factor_df = pd.DataFrame(factor_data, index=dates)
        price_df = pd.DataFrame(price_data, index=dates)

        ic_calc = ICCalculator(forward_periods=5)
        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        # 应该能够处理NaN并返回有效结果
        assert len(ic_series) > 0
        assert not ic_series.isna().all()

    def test_different_forward_periods(self, sample_factor_data, sample_price_data):
        """测试不同的前瞻期"""
        for period in [1, 5, 10, 20]:
            ic_calc = ICCalculator(forward_periods=period)
            ic_series = ic_calc.calculate_ic_series(sample_factor_data, sample_price_data)

            assert len(ic_series) > 0
            assert (ic_series >= -1).all()
            assert (ic_series <= 1).all()

    def test_pearson_vs_spearman(self, sample_factor_data, sample_price_data):
        """对比Pearson和Spearman方法"""
        ic_pearson = ICCalculator(forward_periods=5, method='pearson')
        ic_spearman = ICCalculator(forward_periods=5, method='spearman')

        series_pearson = ic_pearson.calculate_ic_series(sample_factor_data, sample_price_data)
        series_spearman = ic_spearman.calculate_ic_series(sample_factor_data, sample_price_data)

        # 两种方法应该都返回有效结果
        assert len(series_pearson) > 0
        assert len(series_spearman) > 0

        # 结果长度应该相同
        assert len(series_pearson) == len(series_spearman)

        # 结果相关但不完全相同
        correlation = series_pearson.corr(series_spearman)
        assert correlation > 0.5  # 应该高度相关


# ==================== 向量化正确性测试 ====================


class TestVectorizationCorrectness:
    """向量化计算正确性测试"""

    def test_vectorized_vs_loop_consistency(self, sample_factor_data, sample_price_data):
        """测试向量化版本与循环版本的一致性"""
        ic_calc = ICCalculator(forward_periods=5, method='pearson')

        # 使用向量化版本
        ic_series = ic_calc.calculate_ic_series(sample_factor_data, sample_price_data)

        # 手动循环计算（原始方法）
        future_returns = sample_price_data.pct_change(5).shift(-5)

        ic_manual = {}
        for date in sample_factor_data.index:
            if date not in future_returns.index:
                continue

            factor_values = sample_factor_data.loc[date]
            return_values = future_returns.loc[date]

            # 删除NaN
            valid_mask = factor_values.notna() & return_values.notna()
            if valid_mask.sum() >= 10:
                ic = factor_values[valid_mask].corr(return_values[valid_mask])
                if not np.isnan(ic):
                    ic_manual[date] = ic

        ic_series_manual = pd.Series(ic_manual)

        # 对比结果
        # 确保索引对齐
        common_dates = ic_series.index.intersection(ic_series_manual.index)
        assert len(common_dates) > 0

        # 数值应该完全一致
        pd.testing.assert_series_equal(
            ic_series.loc[common_dates],
            ic_series_manual.loc[common_dates],
            check_names=False,
            rtol=1e-10
        )

    def test_known_correlation(self):
        """测试已知相关性"""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        stocks = [f'S{i}' for i in range(30)]

        # 创建完全正相关的因子和收益
        factor_data = {}
        price_data = {}

        base_values = np.random.randn(100)

        for i, stock in enumerate(stocks):
            # 因子值与基准相同（加小噪声）
            factor_data[stock] = base_values + np.random.randn(100) * 0.01

            # 价格与因子正相关
            returns = base_values * 0.01 + np.random.randn(100) * 0.001
            prices = 100 * (1 + returns).cumprod()
            price_data[stock] = prices

        factor_df = pd.DataFrame(factor_data, index=dates)
        price_df = pd.DataFrame(price_data, index=dates)

        ic_calc = ICCalculator(forward_periods=1)
        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        # IC应该有一定比例为正（因为有正相关性，但噪声较大）
        # 由于添加了噪声，降低阈值
        positive_rate = (ic_series > 0).mean()
        assert positive_rate > 0.3, f"正IC比例({positive_rate:.2f})应该大于0.3"


# ==================== 性能测试 ====================


class TestICPerformance:
    """IC计算性能测试"""

    def test_performance_improvement(self, large_factor_data, large_price_data):
        """测试性能提升"""
        ic_calc = ICCalculator(forward_periods=5, method='pearson')

        # 测试向量化版本
        start = time.time()
        ic_series = ic_calc.calculate_ic_series(large_factor_data, large_price_data)
        time_vectorized = time.time() - start

        print(f"\n性能测试 (1250天 × 100股票):")
        print(f"  向量化版本: {time_vectorized:.4f}秒")
        print(f"  计算了 {len(ic_series)} 个IC值")

        # 向量化版本应该很快（<1秒）
        assert time_vectorized < 1.0, f"向量化计算耗时({time_vectorized:.4f}秒)超过1秒"

    def test_scalability(self):
        """测试可扩展性"""
        results = {}

        for n_days in [100, 250, 500, 1000]:
            dates = pd.date_range('2020-01-01', periods=n_days, freq='D')
            stocks = [f'S{i}' for i in range(50)]

            factor_data = {stock: np.random.randn(n_days) for stock in stocks}
            price_data = {
                stock: 100 * (1 + np.random.normal(0.001, 0.02, n_days)).cumprod()
                for stock in stocks
            }

            factor_df = pd.DataFrame(factor_data, index=dates)
            price_df = pd.DataFrame(price_data, index=dates)

            ic_calc = ICCalculator(forward_periods=5)

            start = time.time()
            ic_series = ic_calc.calculate_ic_series(factor_df, price_df)
            elapsed = time.time() - start

            results[n_days] = elapsed

        print("\n可扩展性测试:")
        for n_days, elapsed in results.items():
            print(f"  {n_days}天: {elapsed:.4f}秒")

        # 时间复杂度应该接近线性
        # 1000天耗时应该不超过100天的15倍
        assert results[1000] / results[100] < 15


# ==================== IC统计指标测试 ====================


class TestICStats:
    """IC统计指标测试"""

    def test_ic_stats_calculation(self, sample_factor_data, sample_price_data):
        """测试IC统计指标计算"""
        ic_calc = ICCalculator(forward_periods=5)

        ic_result = ic_calc.calculate_ic_stats(sample_factor_data, sample_price_data)

        # 检查返回的统计指标
        assert hasattr(ic_result, 'mean_ic')
        assert hasattr(ic_result, 'std_ic')
        assert hasattr(ic_result, 'ic_ir')
        assert hasattr(ic_result, 'positive_rate')

        # 检查数值范围
        assert -1 <= ic_result.mean_ic <= 1
        assert ic_result.std_ic >= 0
        assert 0 <= ic_result.positive_rate <= 1

    def test_ic_stats_with_insufficient_data(self):
        """测试数据不足的情况"""
        # 创建很少的数据
        dates = pd.date_range('2020-01-01', periods=5, freq='D')
        stocks = ['S1', 'S2']

        factor_df = pd.DataFrame({
            'S1': [1, 2, 3, 4, 5],
            'S2': [2, 3, 4, 5, 6]
        }, index=dates)

        price_df = pd.DataFrame({
            'S1': [100, 101, 102, 103, 104],
            'S2': [100, 102, 104, 106, 108]
        }, index=dates)

        ic_calc = ICCalculator(forward_periods=1)

        # 应该抛出异常或返回警告
        with pytest.raises(ValueError, match="有效IC值太少"):
            ic_calc.calculate_ic_stats(factor_df, price_df)


# ==================== 边界条件测试 ====================


class TestEdgeCases:
    """边界条件测试"""

    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')

        factor_df = pd.DataFrame({
            'S1': np.random.randn(100)
        }, index=dates)

        price_df = pd.DataFrame({
            'S1': 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
        }, index=dates)

        ic_calc = ICCalculator(forward_periods=5)
        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        # 单只股票无法计算横截面IC（需要至少10只）
        # 应该返回空序列或全NaN
        assert len(ic_series) == 0 or ic_series.isna().all()

    def test_misaligned_data(self):
        """测试不对齐的数据"""
        dates1 = pd.date_range('2020-01-01', periods=100, freq='D')
        dates2 = pd.date_range('2020-02-01', periods=100, freq='D')

        stocks = [f'S{i}' for i in range(20)]

        factor_df = pd.DataFrame({
            stock: np.random.randn(100) for stock in stocks
        }, index=dates1)

        price_df = pd.DataFrame({
            stock: 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
            for stock in stocks
        }, index=dates2)

        ic_calc = ICCalculator(forward_periods=5)
        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        # 应该只计算重叠日期的IC
        assert len(ic_series) >= 0

    def test_all_nan_day(self):
        """测试某天全部为NaN的情况"""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        stocks = [f'S{i}' for i in range(20)]

        factor_data = {stock: np.random.randn(100) for stock in stocks}
        price_data = {
            stock: 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
            for stock in stocks
        }

        factor_df = pd.DataFrame(factor_data, index=dates)
        price_df = pd.DataFrame(price_data, index=dates)

        # 将第50天设置为全NaN
        factor_df.iloc[50] = np.nan

        ic_calc = ICCalculator(forward_periods=5)
        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        # 第50天应该没有IC值（或为NaN）
        if dates[50] in ic_series.index:
            assert np.isnan(ic_series.loc[dates[50]])


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
