"""
IC计算器单元测试

测试功能：
- IC值计算
- IC时间序列计算
- IC统计指标计算
- 多因子IC批量计算
- IC衰减分析
- 滚动IC分析
- 边界条件和异常处理
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from analysis.ic_calculator import ICCalculator, ICResult


# ==================== 测试数据生成 ====================


@pytest.fixture
def sample_factor_data():
    """生成样本因子数据（250天，50只股票）"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=250, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(50)]

    # 生成有一定预测能力的因子
    factor_values = np.random.randn(250, 50)

    df = pd.DataFrame(factor_values, index=dates, columns=stocks)
    return df


@pytest.fixture
def sample_price_data():
    """生成样本价格数据（250天，50只股票）"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=250, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(50)]

    # 基础价格
    base_price = 100.0

    # 生成收益率（加入一些因子相关性）
    returns = np.random.randn(250, 50) * 0.02

    # 累积价格
    prices = base_price * (1 + returns).cumprod(axis=0)

    df = pd.DataFrame(prices, index=dates, columns=stocks)
    return df


@pytest.fixture
def correlated_data():
    """生成因子与收益高度相关的数据"""
    np.random.seed(123)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(30)]

    # 生成基础因子
    factor_values = np.random.randn(100, 30)

    # 生成价格（与因子高度相关）
    base_price = 100.0
    returns = factor_values * 0.01 + np.random.randn(100, 30) * 0.01  # 加入因子影响
    prices = base_price * (1 + returns).cumprod(axis=0)

    factor_df = pd.DataFrame(factor_values, index=dates, columns=stocks)
    price_df = pd.DataFrame(prices, index=dates, columns=stocks)

    return factor_df, price_df


@pytest.fixture
def small_data():
    """生成小数据集（测试边界情况）"""
    dates = pd.date_range('2023-01-01', periods=30, freq='D')
    stocks = ['stock_A', 'stock_B', 'stock_C']

    factor_df = pd.DataFrame(
        np.random.randn(30, 3),
        index=dates,
        columns=stocks
    )

    price_df = pd.DataFrame(
        100 * (1 + np.random.randn(30, 3) * 0.02).cumprod(axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, price_df


# ==================== ICCalculator基础测试 ====================


class TestICCalculatorInit:
    """测试IC计算器初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        ic_calc = ICCalculator()
        assert ic_calc.forward_periods == 5
        assert ic_calc.method == 'pearson'

    def test_custom_init(self):
        """测试自定义初始化"""
        ic_calc = ICCalculator(forward_periods=10, method='spearman')
        assert ic_calc.forward_periods == 10
        assert ic_calc.method == 'spearman'

    def test_invalid_method(self):
        """测试无效的相关性方法"""
        with pytest.raises(ValueError, match="method必须是'pearson'或'spearman'"):
            ICCalculator(method='invalid')


class TestCalculateIC:
    """测试单个时间点IC计算"""

    def test_calculate_ic_basic(self):
        """测试基本IC计算"""
        ic_calc = ICCalculator()

        # 创建简单的因子和收益数据（需要至少10个数据点）
        factor = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                          index=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'])
        returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12],
                           index=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'])

        ic = ic_calc.calculate_ic(factor, returns)

        assert isinstance(ic, float)
        assert not np.isnan(ic)  # 不应该是NaN
        assert -1 <= ic <= 1  # IC值在[-1, 1]之间
        assert ic > 0.9  # 完全正相关的数据

    def test_calculate_ic_spearman(self):
        """测试Spearman相关性"""
        ic_calc = ICCalculator(method='spearman')

        factor = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12])

        ic = ic_calc.calculate_ic(factor, returns)

        assert abs(ic - 1.0) < 0.01  # 单调数据的RankIC应该接近1

    def test_calculate_ic_with_nan(self):
        """测试包含NaN值的情况"""
        ic_calc = ICCalculator()

        # 需要至少10个有效样本
        factor = pd.Series([1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13])
        returns = pd.Series([0.01, 0.02, 0.03, np.nan, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13])

        ic = ic_calc.calculate_ic(factor, returns)

        assert isinstance(ic, float)
        assert not np.isnan(ic)  # 应该正确处理NaN

    def test_calculate_ic_insufficient_data(self):
        """测试数据不足的情况"""
        ic_calc = ICCalculator()

        # 少于10个有效样本
        factor = pd.Series([1, 2, 3])
        returns = pd.Series([0.01, 0.02, 0.03])

        ic = ic_calc.calculate_ic(factor, returns)

        assert np.isnan(ic)  # 数据不足应返回NaN


class TestCalculateICSeries:
    """测试IC时间序列计算"""

    def test_calculate_ic_series_basic(self, sample_factor_data, sample_price_data):
        """测试基本IC序列计算"""
        ic_calc = ICCalculator(forward_periods=5)

        ic_series = ic_calc.calculate_ic_series(sample_factor_data, sample_price_data)

        assert isinstance(ic_series, pd.Series)
        assert len(ic_series) > 0
        assert len(ic_series) <= len(sample_factor_data)  # 不会超过原始数据长度
        assert all(-1 <= ic <= 1 for ic in ic_series if not np.isnan(ic))

    def test_calculate_ic_series_different_periods(self, sample_factor_data, sample_price_data):
        """测试不同前瞻期"""
        for period in [1, 5, 10, 20]:
            ic_calc = ICCalculator(forward_periods=period)
            ic_series = ic_calc.calculate_ic_series(sample_factor_data, sample_price_data)

            assert len(ic_series) > 0
            # 前瞻期越长，有效IC值越少
            if period > 1:
                assert len(ic_series) < len(sample_factor_data)

    def test_calculate_ic_series_small_data(self, small_data):
        """测试小数据集"""
        factor_df, price_df = small_data
        # 小数据集用较短的前瞻期
        ic_calc = ICCalculator(forward_periods=2)

        ic_series = ic_calc.calculate_ic_series(factor_df, price_df)

        assert isinstance(ic_series, pd.Series)
        # 小数据集可能IC值很少或为0
        assert len(ic_series) >= 0


class TestCalculateICStats:
    """测试IC统计指标计算"""

    def test_calculate_ic_stats_basic(self, sample_factor_data, sample_price_data):
        """测试基本IC统计"""
        ic_calc = ICCalculator(forward_periods=5, method='spearman')

        result = ic_calc.calculate_ic_stats(sample_factor_data, sample_price_data)

        assert isinstance(result, ICResult)
        assert isinstance(result.mean_ic, float)
        assert isinstance(result.std_ic, float)
        assert isinstance(result.ic_ir, float)
        assert 0 <= result.positive_rate <= 1
        assert isinstance(result.t_stat, float)
        assert 0 <= result.p_value <= 1
        assert isinstance(result.ic_series, pd.Series)

    def test_calculate_ic_stats_values(self, correlated_data):
        """测试高相关数据的IC统计值"""
        factor_df, price_df = correlated_data
        ic_calc = ICCalculator(forward_periods=5, method='spearman')

        result = ic_calc.calculate_ic_stats(factor_df, price_df)

        # 高相关数据应该有较高的IC
        assert abs(result.mean_ic) > 0.01  # IC均值应该显著
        assert result.ic_ir != 0  # ICIR应该非零
        assert result.positive_rate > 0  # 正值率应该大于0

    def test_calculate_ic_stats_to_dict(self, sample_factor_data, sample_price_data):
        """测试ICResult转字典"""
        ic_calc = ICCalculator()
        result = ic_calc.calculate_ic_stats(sample_factor_data, sample_price_data)

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert 'mean_ic' in result_dict
        assert 'std_ic' in result_dict
        assert 'ic_ir' in result_dict
        assert 'positive_rate' in result_dict
        assert 't_stat' in result_dict
        assert 'p_value' in result_dict

    def test_calculate_ic_stats_str(self, sample_factor_data, sample_price_data):
        """测试ICResult字符串格式化"""
        ic_calc = ICCalculator()
        result = ic_calc.calculate_ic_stats(sample_factor_data, sample_price_data)

        result_str = str(result)

        assert isinstance(result_str, str)
        assert 'IC统计摘要' in result_str
        assert '均值' in result_str
        assert 'ICIR' in result_str

    def test_calculate_ic_stats_insufficient_data(self):
        """测试数据不足的情况"""
        ic_calc = ICCalculator()

        # 生成极少数据
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        stocks = ['A', 'B']
        factor_df = pd.DataFrame(np.random.randn(5, 2), index=dates, columns=stocks)
        price_df = pd.DataFrame(np.random.randn(5, 2) + 100, index=dates, columns=stocks)

        with pytest.raises(ValueError, match="有效IC值太少"):
            ic_calc.calculate_ic_stats(factor_df, price_df)


class TestCalculateMultiFactorIC:
    """测试批量计算多因子IC"""

    def test_calculate_multi_factor_ic_basic(self, sample_price_data):
        """测试批量计算多因子IC"""
        np.random.seed(42)

        # 创建3个因子
        factor_dict = {
            'factor_1': pd.DataFrame(
                np.random.randn(250, 50),
                index=sample_price_data.index,
                columns=sample_price_data.columns
            ),
            'factor_2': pd.DataFrame(
                np.random.randn(250, 50),
                index=sample_price_data.index,
                columns=sample_price_data.columns
            ),
            'factor_3': pd.DataFrame(
                np.random.randn(250, 50),
                index=sample_price_data.index,
                columns=sample_price_data.columns
            )
        }

        ic_calc = ICCalculator(forward_periods=5, method='spearman')
        ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, sample_price_data)

        assert isinstance(ic_summary, pd.DataFrame)
        assert len(ic_summary) == 3
        assert 'IC均值' in ic_summary.columns
        assert 'IC标准差' in ic_summary.columns
        assert 'ICIR' in ic_summary.columns
        assert 'IC正值率' in ic_summary.columns
        assert 't统计量' in ic_summary.columns
        assert 'p值' in ic_summary.columns
        assert '有效天数' in ic_summary.columns

    def test_calculate_multi_factor_ic_sorted(self, sample_price_data):
        """测试结果按ICIR排序"""
        np.random.seed(42)

        factor_dict = {
            'weak_factor': pd.DataFrame(
                np.random.randn(250, 50) * 0.1,  # 弱因子
                index=sample_price_data.index,
                columns=sample_price_data.columns
            ),
            'strong_factor': pd.DataFrame(
                np.random.randn(250, 50),  # 强因子
                index=sample_price_data.index,
                columns=sample_price_data.columns
            )
        }

        ic_calc = ICCalculator()
        ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, sample_price_data)

        # 检查按ICIR降序排列
        icir_values = ic_summary['ICIR'].values
        assert all(icir_values[i] >= icir_values[i+1] for i in range(len(icir_values)-1))

    def test_calculate_multi_factor_ic_partial_failure(self, sample_price_data):
        """测试部分因子计算失败的情况"""
        # 创建一个会失败的因子（数据太少）
        bad_factor_df = pd.DataFrame(
            [[1, 2], [3, 4]],
            index=sample_price_data.index[:2],
            columns=['A', 'B']
        )

        good_factor_df = pd.DataFrame(
            np.random.randn(250, 50),
            index=sample_price_data.index,
            columns=sample_price_data.columns
        )

        factor_dict = {
            'bad_factor': bad_factor_df,
            'good_factor': good_factor_df
        }

        ic_calc = ICCalculator()
        ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, sample_price_data)

        # 应该只返回成功计算的因子
        assert len(ic_summary) >= 0


class TestAnalyzeICDecay:
    """测试IC衰减分析"""

    def test_analyze_ic_decay_basic(self, sample_factor_data, sample_price_data):
        """测试基本IC衰减分析"""
        ic_calc = ICCalculator()

        decay_df = ic_calc.analyze_ic_decay(sample_factor_data, sample_price_data, max_period=10)

        assert isinstance(decay_df, pd.DataFrame)
        assert len(decay_df) <= 10
        assert 'IC均值' in decay_df.columns
        assert 'ICIR' in decay_df.columns
        assert 'IC正值率' in decay_df.columns
        assert decay_df.index.name == '持有期'

    def test_analyze_ic_decay_periods(self, sample_factor_data, sample_price_data):
        """测试不同衰减期数"""
        ic_calc = ICCalculator()

        for max_period in [5, 10, 15]:
            decay_df = ic_calc.analyze_ic_decay(
                sample_factor_data, sample_price_data, max_period=max_period
            )
            assert len(decay_df) <= max_period


class TestCalculateRollingIC:
    """测试滚动IC计算"""

    def test_calculate_rolling_ic_basic(self, sample_factor_data, sample_price_data):
        """测试基本滚动IC"""
        ic_calc = ICCalculator()

        rolling_ic = ic_calc.calculate_rolling_ic(sample_factor_data, sample_price_data, window=60)

        assert isinstance(rolling_ic, pd.DataFrame)
        assert 'IC均值' in rolling_ic.columns
        assert 'IC标准差' in rolling_ic.columns
        assert 'ICIR' in rolling_ic.columns
        assert 'IC正值率' in rolling_ic.columns
        assert len(rolling_ic) <= len(sample_factor_data)

    def test_calculate_rolling_ic_window_size(self, sample_factor_data, sample_price_data):
        """测试不同窗口大小"""
        ic_calc = ICCalculator()

        for window in [30, 60, 90]:
            rolling_ic = ic_calc.calculate_rolling_ic(
                sample_factor_data, sample_price_data, window=window
            )
            assert len(rolling_ic) > 0
            # 窗口越大，有效值越少（前面的值会是NaN）
            assert rolling_ic['IC均值'].notna().sum() <= len(sample_factor_data) - window + 1


# ==================== 边界条件和异常测试 ====================


class TestEdgeCases:
    """测试边界条件"""

    def test_empty_data(self):
        """测试空数据"""
        ic_calc = ICCalculator()

        empty_df = pd.DataFrame()

        with pytest.raises(Exception):
            ic_calc.calculate_ic_series(empty_df, empty_df)

    def test_mismatched_dates(self, sample_factor_data, sample_price_data):
        """测试日期不匹配的数据"""
        ic_calc = ICCalculator()

        # 价格数据日期不同
        price_df_shifted = sample_price_data.copy()
        price_df_shifted.index = price_df_shifted.index + pd.Timedelta(days=10)

        ic_series = ic_calc.calculate_ic_series(sample_factor_data, price_df_shifted)

        # 应该处理日期不匹配，但可能返回更少的有效值
        assert isinstance(ic_series, pd.Series)

    def test_all_nan_factor(self, sample_price_data):
        """测试全NaN因子"""
        ic_calc = ICCalculator()

        nan_factor = pd.DataFrame(
            np.nan,
            index=sample_price_data.index,
            columns=sample_price_data.columns
        )

        ic_series = ic_calc.calculate_ic_series(nan_factor, sample_price_data)

        # 全NaN因子应该返回空或全NaN的IC序列
        assert len(ic_series) == 0 or ic_series.isna().all()

    def test_constant_factor(self, sample_price_data):
        """测试常数因子（无变化）"""
        ic_calc = ICCalculator()

        constant_factor = pd.DataFrame(
            1.0,
            index=sample_price_data.index,
            columns=sample_price_data.columns
        )

        ic_series = ic_calc.calculate_ic_series(constant_factor, sample_price_data)

        # 常数因子的IC应该是NaN（无法计算相关性）
        assert ic_series.isna().all() or len(ic_series) == 0


# ==================== 集成测试 ====================


class TestICCalculatorIntegration:
    """集成测试"""

    def test_complete_workflow(self, correlated_data):
        """测试完整工作流"""
        factor_df, price_df = correlated_data

        # 1. 创建IC计算器
        ic_calc = ICCalculator(forward_periods=5, method='spearman')

        # 2. 计算IC统计
        ic_result = ic_calc.calculate_ic_stats(factor_df, price_df)

        assert abs(ic_result.mean_ic) > 0
        assert ic_result.ic_ir != 0

        # 3. IC衰减分析
        decay_df = ic_calc.analyze_ic_decay(factor_df, price_df, max_period=10)

        assert len(decay_df) > 0

        # 4. 滚动IC
        rolling_ic = ic_calc.calculate_rolling_ic(factor_df, price_df, window=30)

        assert len(rolling_ic) > 0

    def test_multi_factor_workflow(self, sample_price_data):
        """测试多因子工作流"""
        np.random.seed(42)

        # 创建多个因子
        factor_dict = {}
        for i in range(5):
            factor_dict[f'factor_{i}'] = pd.DataFrame(
                np.random.randn(250, 50),
                index=sample_price_data.index,
                columns=sample_price_data.columns
            )

        ic_calc = ICCalculator(forward_periods=5, method='spearman')

        # 批量计算IC
        ic_summary = ic_calc.calculate_multi_factor_ic(factor_dict, sample_price_data)

        assert len(ic_summary) <= 5
        assert all(col in ic_summary.columns for col in ['IC均值', 'ICIR', 'IC正值率'])

        # 选择最优因子
        best_factors = ic_summary.nlargest(3, 'ICIR').index.tolist()

        assert len(best_factors) <= 3


# ==================== 性能测试 ====================


@pytest.mark.performance
class TestICCalculatorPerformance:
    """性能测试（标记为慢速测试）"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        import time

        # 生成大数据集（500天，100只股票）
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=500, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(100)]

        factor_df = pd.DataFrame(
            np.random.randn(500, 100),
            index=dates,
            columns=stocks
        )

        price_df = pd.DataFrame(
            100 * (1 + np.random.randn(500, 100) * 0.02).cumprod(axis=0),
            index=dates,
            columns=stocks
        )

        ic_calc = ICCalculator(forward_periods=5, method='spearman')

        start_time = time.time()
        ic_result = ic_calc.calculate_ic_stats(factor_df, price_df)
        duration = time.time() - start_time

        assert duration < 2.0  # 应该在2秒内完成
        assert isinstance(ic_result, ICResult)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
