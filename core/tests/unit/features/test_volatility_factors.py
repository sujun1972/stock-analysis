"""
波动率因子计算器专项测试

测试 VolatilityFactorCalculator 的所有功能：
- 历史波动率(VOLATILITY)
- 波动率偏度(VOLSKEW)
- Parkinson波动率(PARKINSON_VOL)
- 边界情况和异常处理

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np

from src.features.alpha_factors import VolatilityFactorCalculator


# ==================== Fixtures ====================


@pytest.fixture
def sample_ohlc_data():
    """生成OHLC数据"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 200)
    close_prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'open': close_prices * (1 + np.random.uniform(-0.01, 0.01, 200)),
        'high': close_prices * (1 + np.random.uniform(0, 0.03, 200)),
        'low': close_prices * (1 + np.random.uniform(-0.03, 0, 200)),
        'close': close_prices,
    }, index=dates)


@pytest.fixture
def high_volatility_data():
    """生成高波动率数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 大幅波动
    returns = np.random.normal(0, 0.05, 100)
    prices = 100 * (1 + returns).cumprod()

    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.05,
        'low': prices * 0.95
    }, index=dates)


@pytest.fixture
def low_volatility_data():
    """生成低波动率数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 小幅波动
    returns = np.random.normal(0, 0.005, 100)
    prices = 100 * (1 + returns).cumprod()

    return pd.DataFrame({
        'close': prices,
        'high': prices * 1.005,
        'low': prices * 0.995
    }, index=dates)


# ==================== 基础功能测试 ====================


class TestVolatilityFactorBasics:
    """测试波动率因子计算器的基础功能"""

    def test_calculator_initialization(self, sample_ohlc_data):
        """测试计算器初始化"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        assert calc.df is not None
        assert 'close' in calc.df.columns

    def test_validation_missing_close(self):
        """测试缺少close列时抛出异常"""
        df = pd.DataFrame({'high': [100, 101], 'low': [98, 99]})
        with pytest.raises(ValueError, match="缺少必需的列: close"):
            VolatilityFactorCalculator(df)


# ==================== 历史波动率测试 ====================


class TestHistoricalVolatility:
    """测试历史波动率因子"""

    def test_volatility_basic(self, sample_ohlc_data):
        """测试基础波动率计算"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_volatility_factors(periods=[20])

        assert 'VOLATILITY20' in result.columns
        assert 'VOLSKEW20' in result.columns

    def test_volatility_multiple_periods(self, sample_ohlc_data):
        """测试多周期波动率"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        periods = [5, 10, 20, 60]
        result = calc.add_volatility_factors(periods=periods)

        for period in periods:
            assert f'VOLATILITY{period}' in result.columns
            assert f'VOLSKEW{period}' in result.columns

    def test_volatility_always_positive(self, sample_ohlc_data):
        """测试波动率总是非负"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_volatility_factors(periods=[20])

        valid_vol = result['VOLATILITY20'].dropna()
        assert (valid_vol >= 0).all()

    def test_high_vol_larger_than_low_vol(self):
        """测试高波动率数据产生更大的波动率值"""
        # 创建低波动率数据
        np.random.seed(42)
        low_vol_prices = 100 * (1 + np.random.normal(0, 0.005, 100)).cumprod()
        df_low = pd.DataFrame({'close': low_vol_prices})

        # 创建高波动率数据（使用不同的随机种子确保数据不同）
        np.random.seed(777)
        high_vol_prices = 100 * (1 + np.random.normal(0, 0.03, 100)).cumprod()
        df_high = pd.DataFrame({'close': high_vol_prices})

        # 计算波动率
        calc_low = VolatilityFactorCalculator(df_low)
        result_low = calc_low.add_volatility_factors(periods=[20])

        calc_high = VolatilityFactorCalculator(df_high)
        result_high = calc_high.add_volatility_factors(periods=[20])

        # 验证高波动率数据产生更大的波动率值
        avg_vol_low = result_low['VOLATILITY20'].dropna().mean()
        avg_vol_high = result_high['VOLATILITY20'].dropna().mean()

        assert avg_vol_high > avg_vol_low, f"高波动率({avg_vol_high:.2f})应大于低波动率({avg_vol_low:.2f})"
        assert avg_vol_low > 0, "低波动率应为正数"
        assert avg_vol_high < 200, "年化波动率不应超过200%"

    def test_volatility_annualization(self, sample_ohlc_data):
        """测试波动率年化"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_volatility_factors(periods=[20])

        # 波动率应该是合理的年化值（通常0-100%）
        valid_vol = result['VOLATILITY20'].dropna()
        assert valid_vol.min() >= 0
        assert valid_vol.max() < 200  # 年化波动率一般不会超过200%

    def test_volskew_calculation(self, sample_ohlc_data):
        """测试波动率偏度计算"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_volatility_factors(periods=[20])

        # 偏度可以是正值或负值
        valid_skew = result['VOLSKEW20'].dropna()
        assert len(valid_skew) > 0
        # 偏度通常在-3到3之间
        assert valid_skew.min() > -10
        assert valid_skew.max() < 10

    def test_constant_price_zero_volatility(self):
        """测试价格不变时波动率为0"""
        df = pd.DataFrame({'close': [100] * 50})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[10])

        valid_vol = result['VOLATILITY10'].dropna()
        assert (valid_vol == 0).all()


# ==================== Parkinson波动率测试 ====================


class TestParkinsonVolatility:
    """测试Parkinson波动率（基于高低价）"""

    def test_parkinson_basic(self, sample_ohlc_data):
        """测试基础Parkinson波动率计算"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_high_low_volatility(periods=[10])

        assert 'PARKINSON_VOL10' in result.columns

    def test_parkinson_multiple_periods(self, sample_ohlc_data):
        """测试多周期Parkinson波动率"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        periods = [10, 20]
        result = calc.add_high_low_volatility(periods=periods)

        for period in periods:
            assert f'PARKINSON_VOL{period}' in result.columns

    def test_parkinson_always_positive(self, sample_ohlc_data):
        """测试Parkinson波动率总是非负"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_high_low_volatility(periods=[10])

        valid_vol = result['PARKINSON_VOL10'].dropna()
        assert (valid_vol >= 0).all()

    def test_parkinson_missing_high_low(self):
        """测试缺少high/low列时的处理"""
        df = pd.DataFrame({'close': [100, 101, 102, 103, 104] * 5})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_high_low_volatility(periods=[10])

        # 应该不会生成Parkinson波动率
        assert 'PARKINSON_VOL10' not in result.columns

    def test_parkinson_larger_range_larger_vol(self):
        """测试高低价差大时Parkinson波动率更大"""
        # 小波动范围
        df1 = pd.DataFrame({
            'close': [100] * 30,
            'high': [101] * 30,
            'low': [99] * 30
        })

        # 大波动范围
        df2 = pd.DataFrame({
            'close': [100] * 30,
            'high': [110] * 30,
            'low': [90] * 30
        })

        calc1 = VolatilityFactorCalculator(df1)
        result1 = calc1.add_high_low_volatility(periods=[10])

        calc2 = VolatilityFactorCalculator(df2)
        result2 = calc2.add_high_low_volatility(periods=[10])

        avg_vol1 = result1['PARKINSON_VOL10'].mean()
        avg_vol2 = result2['PARKINSON_VOL10'].mean()

        assert avg_vol2 > avg_vol1


# ==================== 综合测试 ====================


class TestVolatilityCalculateAll:
    """测试calculate_all方法"""

    def test_calculate_all_basic(self, sample_ohlc_data):
        """测试计算所有波动率因子"""
        calc = VolatilityFactorCalculator(sample_ohlc_data.copy())
        resp = calc.calculate_all()
        result = resp.data if hasattr(resp, 'data') else resp

        # 检查历史波动率
        assert any('VOLATILITY' in col for col in result.columns)
        # 检查Parkinson波动率
        assert any('PARKINSON' in col for col in result.columns)

    def test_calculate_all_without_high_low(self):
        """测试只有close列时calculate_all"""
        df = pd.DataFrame({'close': np.random.randn(100).cumsum() + 100})
        calc = VolatilityFactorCalculator(df)
        resp = calc.calculate_all()
        result = resp.data if hasattr(resp, 'data') else resp

        # 应该有历史波动率，但没有Parkinson波动率
        assert any('VOLATILITY' in col for col in result.columns)


# ==================== 边界情况测试 ====================


class TestVolatilityEdgeCases:
    """测试边界情况"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({'close': [100]})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[5])

        assert result['VOLATILITY5'].isna().all()

    def test_small_dataset(self):
        """测试小数据集"""
        df = pd.DataFrame({'close': [100, 101, 102]})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[10])

        # 数据不足，应该是NaN
        assert result['VOLATILITY10'].isna().all()

    def test_all_nan_prices(self):
        """测试价格全为NaN"""
        df = pd.DataFrame({'close': [np.nan] * 30})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[5])

        assert result['VOLATILITY5'].isna().all()

    def test_extreme_volatility(self):
        """测试极端波动"""
        # 创建真正的极端波动数据
        prices = [100]
        np.random.seed(999)
        for i in range(1, 50):
            # 随机大幅波动
            change = np.random.choice([0.5, 1.5, 0.7, 1.3])
            prices.append(prices[-1] * change)

        df = pd.DataFrame({'close': prices})
        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[10])

        # 应该能处理，不崩溃
        assert 'VOLATILITY10' in result.columns
        valid_vol = result['VOLATILITY10'].dropna()
        assert len(valid_vol) > 0


# ==================== 性能测试 ====================


class TestVolatilityPerformance:
    """测试性能"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        dates = pd.date_range('2020-01-01', periods=1000, freq='D')
        df = pd.DataFrame({
            'close': np.random.randn(1000).cumsum() + 100,
            'high': np.random.randn(1000).cumsum() + 105,
            'low': np.random.randn(1000).cumsum() + 95
        }, index=dates)

        import time
        start = time.time()
        calc = VolatilityFactorCalculator(df)
        resp = calc.calculate_all()
        result = resp.data if hasattr(resp, 'data') else resp
        elapsed = time.time() - start

        assert elapsed < 1.0
        assert len(result) == 1000
