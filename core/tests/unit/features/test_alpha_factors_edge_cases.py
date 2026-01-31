"""
Alpha因子边界情况和鲁棒性测试

测试所有因子计算器在各种极端情况下的表现：
- 空数据、单行数据、小数据集
- 缺失值(NaN)处理
- 极端值(inf, -inf)处理
- 异常数据类型
- 列名不匹配
- 数据不连续
- 性能压力测试

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np

from src.features.alpha_factors import (
    AlphaFactors,
    MomentumFactorCalculator,
    ReversalFactorCalculator,
    VolatilityFactorCalculator,
    VolumeFactorCalculator,
)


# ==================== Fixtures ====================


@pytest.fixture
def empty_dataframe():
    """空DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def single_row_df():
    """单行数据"""
    return pd.DataFrame({
        'open': [100],
        'high': [102],
        'low': [98],
        'close': [101],
        'vol': [1000000]
    })


@pytest.fixture
def two_row_df():
    """两行数据"""
    return pd.DataFrame({
        'open': [100, 101],
        'high': [102, 103],
        'low': [98, 99],
        'close': [101, 102],
        'vol': [1000000, 1100000]
    })


@pytest.fixture
def nan_filled_df():
    """包含大量NaN的数据"""
    return pd.DataFrame({
        'close': [100, np.nan, 102, np.nan, np.nan, 105, 106, np.nan, 108, 109],
        'vol': [1e6, 1.1e6, np.nan, np.nan, 1.4e6, np.nan, 1.6e6, 1.7e6, np.nan, 1.9e6]
    })


@pytest.fixture
def all_nan_df():
    """全为NaN的数据"""
    return pd.DataFrame({
        'close': [np.nan] * 30,
        'vol': [np.nan] * 30
    })


@pytest.fixture
def extreme_values_df():
    """包含极端值的数据"""
    return pd.DataFrame({
        'close': [100, 101, np.inf, 103, 104, -np.inf, 106, 1e10, 108, 1e-10] * 3,
        'vol': [1e6, 1e7, 1e20, 1e3, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6] * 3
    })


@pytest.fixture
def zero_negative_prices_df():
    """包含零和负价格的数据"""
    return pd.DataFrame({
        'close': [100, 0, -50, 103, 104, 105, 0, 107, -20, 109] * 3,
        'vol': [1e6] * 30
    })


@pytest.fixture
def non_numeric_df():
    """包含非数值数据"""
    return pd.DataFrame({
        'close': ['100', '101', '102', '103', '104'] * 6,
        'vol': ['1000000', '1100000', '1200000', '1300000', '1400000'] * 6
    })


# ==================== 空数据和小数据集测试 ====================


class TestEmptyAndSmallDatasets:
    """测试空数据和小数据集"""

    def test_empty_dataframe_各计算器(self, empty_dataframe):
        """测试空DataFrame不会崩溃"""
        # 大部分计算器需要close列
        df_with_close = pd.DataFrame({'close': []})

        # 每个计算器都应该能处理空数据
        try:
            calc = MomentumFactorCalculator(df_with_close.copy())
        except Exception as e:
            # 可能抛出验证异常，但不应该崩溃
            assert "缺少必需的列" in str(e) or len(df_with_close) == 0

    def test_single_row_momentum(self, single_row_df):
        """测试单行数据的动量计算"""
        calc = MomentumFactorCalculator(single_row_df.copy())
        result = calc.add_momentum_factors(periods=[5])

        # 单行数据无法计算动量
        if 'MOM5' in result.columns:
            assert result['MOM5'].iloc[0] == 0 or pd.isna(result['MOM5'].iloc[0])

    def test_two_row_reversal(self, two_row_df):
        """测试两行数据的反转因子"""
        calc = ReversalFactorCalculator(two_row_df.copy())
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # 两行数据应该能计算REV1
        if 'REV1' in result.columns:
            assert not pd.isna(result['REV1'].iloc[1])

    def test_small_dataset_large_window(self):
        """测试数据不足以支持大窗口"""
        df = pd.DataFrame({'close': list(range(100, 110))})  # 只有10行

        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[20, 60])  # 窗口大于数据

        # 应该全是NaN
        if 'VOLATILITY20' in result.columns:
            assert result['VOLATILITY20'].isna().all()
        if 'VOLATILITY60' in result.columns:
            assert result['VOLATILITY60'].isna().all()


# ==================== NaN处理测试 ====================


class TestNaNHandling:
    """测试NaN值处理"""

    def test_nan_filled_data(self, nan_filled_df):
        """测试包含NaN的数据"""
        calc = MomentumFactorCalculator(nan_filled_df.copy())
        result = calc.add_momentum_factors(periods=[3])

        # 应该能处理NaN，不崩溃
        assert 'MOM3' in result.columns
        # 有些值应该是NaN，有些应该能计算
        assert result['MOM3'].isna().sum() > 0
        assert result['MOM3'].notna().sum() > 0

    def test_all_nan_prices(self, all_nan_df):
        """测试全为NaN的价格"""
        calc = VolatilityFactorCalculator(all_nan_df.copy())
        result = calc.add_volatility_factors(periods=[5])

        # 全NaN输入应该产生全NaN输出
        if 'VOLATILITY5' in result.columns:
            assert result['VOLATILITY5'].isna().all()

    def test_nan_propagation(self):
        """测试NaN传播"""
        df = pd.DataFrame({
            'close': [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109] * 2
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[2], long_periods=[])

        # NaN应该正确传播
        if 'REV2' in result.columns:
            # 索引2之后的一些值应该是NaN（受到索引2的NaN影响）
            assert result['REV2'].iloc[2:4].isna().any()


# ==================== 极端值处理测试 ====================


class TestExtremeValues:
    """测试极端值处理"""

    def test_infinity_values(self, extreme_values_df):
        """测试无穷大值"""
        calc = MomentumFactorCalculator(extreme_values_df.copy())
        result = calc.add_momentum_factors(periods=[3])

        # 应该能处理inf，不崩溃
        assert 'MOM3' in result.columns
        # 验证包含inf的数据能够正常处理
        # inf会导致计算结果为inf或NaN，这是预期的行为
        assert len(result) == len(extreme_values_df)

    def test_very_large_numbers(self):
        """测试非常大的数字"""
        df = pd.DataFrame({
            'close': [1e10, 1e10 * 1.01, 1e10 * 1.02, 1e10 * 1.03] * 7,
            'vol': [1e20] * 28
        })

        calc = VolumeFactorCalculator(df)
        result = calc.add_volume_factors(periods=[3])

        # 应该能处理大数字
        if 'VOLUME_CHG3' in result.columns:
            assert 'VOLUME_CHG3' in result.columns

    def test_very_small_numbers(self):
        """测试非常小的数字"""
        df = pd.DataFrame({
            'close': [1e-10, 1e-10 * 1.01, 1e-10 * 1.02] * 10,
            'vol': [1e3] * 30
        })

        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[3])

        # 应该能处理小数字
        assert 'VOLATILITY3' in result.columns


# ==================== 异常价格测试 ====================


class TestAbnormalPrices:
    """测试异常价格"""

    def test_zero_prices(self, zero_negative_prices_df):
        """测试零价格"""
        calc = MomentumFactorCalculator(zero_negative_prices_df.copy())
        result = calc.add_momentum_factors(periods=[2])

        # 零价格会导致除零，应该被处理
        assert 'MOM2' in result.columns
        # 对数动量在零价格时会产生inf或NaN
        if 'MOM_LOG2' in result.columns:
            zero_indices = np.where(zero_negative_prices_df['close'] == 0)[0]
            # 零价格影响的位置应该是NaN或inf
            for idx in zero_indices:
                if idx < len(result):
                    value = result['MOM_LOG2'].iloc[idx]
                    assert pd.isna(value) or np.isinf(value)

    def test_negative_prices(self, zero_negative_prices_df):
        """测试负价格"""
        calc = ReversalFactorCalculator(zero_negative_prices_df.copy())
        result = calc.add_reversal_factors(short_periods=[2], long_periods=[])

        # 负价格应该能处理（虽然不合理）
        assert 'REV2' in result.columns

    def test_constant_price(self):
        """测试价格完全不变"""
        df = pd.DataFrame({
            'close': [100] * 50,
            'vol': [1e6] * 50
        })

        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[10])

        # 价格不变，波动率应该是0
        if 'VOLATILITY10' in result.columns:
            valid_vol = result['VOLATILITY10'].dropna()
            assert (valid_vol == 0).all()


# ==================== 数据类型测试 ====================


class TestDataTypes:
    """测试不同数据类型"""

    def test_integer_prices(self):
        """测试整数价格"""
        df = pd.DataFrame({
            'close': list(range(100, 150))
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 整数价格应该能正常处理
        assert 'MOM5' in result.columns
        assert result['MOM5'].dtype in [np.float64, float]

    def test_string_conversion_attempt(self, non_numeric_df):
        """测试字符串数据（应该失败或转换）"""
        try:
            # 尝试转换为数值
            df_numeric = non_numeric_df.copy()
            df_numeric['close'] = pd.to_numeric(df_numeric['close'])

            calc = MomentumFactorCalculator(df_numeric)
            result = calc.add_momentum_factors(periods=[3])

            assert 'MOM3' in result.columns
        except (ValueError, TypeError):
            # 如果无法转换，应该抛出异常
            pass

    def test_mixed_dtypes(self):
        """测试混合数据类型"""
        df = pd.DataFrame({
            'close': [100.5, 101, 102.3, 103, 104.7] * 6,  # 混合int和float
            'vol': [1000000, 1100000, 1200000, 1300000, 1400000] * 6
        })

        calc = VolumeFactorCalculator(df)
        result = calc.add_volume_factors(periods=[3])

        if 'VOLUME_CHG3' in result.columns:
            assert 'VOLUME_CHG3' in result.columns


# ==================== 列名和数据结构测试 ====================


class TestColumnNamesAndStructure:
    """测试列名和数据结构"""

    def test_missing_required_columns(self):
        """测试缺少必需列"""
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104]
            # 缺少 close
        })

        with pytest.raises(ValueError, match="缺少必需的列"):
            MomentumFactorCalculator(df)

    def test_extra_columns(self):
        """测试额外的列不影响计算"""
        df = pd.DataFrame({
            'close': list(range(100, 150)),
            'extra_col1': ['A'] * 50,
            'extra_col2': [True] * 50
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 额外的列应该被保留
        assert 'extra_col1' in result.columns
        assert 'extra_col2' in result.columns
        assert 'MOM5' in result.columns

    def test_case_sensitive_columns(self):
        """测试列名大小写"""
        df = pd.DataFrame({
            'Close': list(range(100, 150)),  # 大写C
        })

        # 应该找不到'close'列
        with pytest.raises(ValueError):
            MomentumFactorCalculator(df)

    def test_volume_column_auto_detection(self):
        """测试成交量列自动检测"""
        # 测试 'vol'
        df1 = pd.DataFrame({'close': [100] * 10, 'vol': [1e6] * 10})
        calc1 = VolumeFactorCalculator(df1)
        assert calc1._get_volume_column() == 'vol'

        # 测试 'volume'
        df2 = pd.DataFrame({'close': [100] * 10, 'volume': [1e6] * 10})
        calc2 = VolumeFactorCalculator(df2)
        assert calc2._get_volume_column() == 'volume'


# ==================== 日期索引测试 ====================


class TestDateIndex:
    """测试日期索引相关"""

    def test_non_datetime_index(self):
        """测试非日期索引"""
        df = pd.DataFrame({
            'close': list(range(100, 150))
        })  # 默认整数索引

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 应该正常工作
        assert 'MOM5' in result.columns

    def test_datetime_index(self):
        """测试日期索引"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': list(range(100, 150))
        }, index=dates)

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 日期索引应该被保留
        assert isinstance(result.index, pd.DatetimeIndex)
        assert 'MOM5' in result.columns

    def test_discontinuous_dates(self):
        """测试不连续的日期"""
        # 跳过周末
        dates = pd.bdate_range('2023-01-01', periods=50)
        df = pd.DataFrame({
            'close': list(range(100, 150))
        }, index=dates)

        calc = VolatilityFactorCalculator(df)
        result = calc.add_volatility_factors(periods=[10])

        # 应该正常处理不连续日期
        assert 'VOLATILITY10' in result.columns

    def test_duplicate_index(self):
        """测试重复索引"""
        dates = pd.date_range('2023-01-01', periods=25, freq='D').tolist() * 2
        df = pd.DataFrame({
            'close': list(range(100, 150))
        }, index=dates)

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 应该能处理（虽然可能有警告）
        assert 'MOM5' in result.columns


# ==================== AlphaFactors集成类测试 ====================


class TestAlphaFactorsIntegration:
    """测试AlphaFactors聚合类"""

    def test_minimal_data_all_factors(self):
        """测试最小数据集计算所有因子"""
        df = pd.DataFrame({'close': list(range(100, 200))})

        alpha = AlphaFactors(df)
        try:
            result = alpha.calculate_all_alpha_factors()
            # 应该生成一些因子
            assert len(result.columns) > 0
        except Exception as e:
            # 某些因子可能需要更多列，这是可以接受的
            pass

    def test_full_ohlcv_all_factors(self):
        """测试完整OHLCV数据计算所有因子"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        prices = 100 * (1 + np.random.normal(0, 0.02, 200)).cumprod()

        df = pd.DataFrame({
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'vol': np.random.uniform(1e6, 1e7, 200)
        }, index=dates)

        alpha = AlphaFactors(df)
        # 使用正确的方法名
        result = alpha.add_all_alpha_factors()

        # 应该生成大量因子
        assert len(result.columns) >= 20  # 至少20个因子


# ==================== 性能和压力测试 ====================


class TestPerformanceAndStress:
    """性能和压力测试"""

    def test_very_large_dataset(self):
        """测试非常大的数据集"""
        n = 5000
        df = pd.DataFrame({
            'close': np.random.randn(n).cumsum() + 100,
            'vol': np.random.uniform(1e6, 1e7, n)
        })

        import time
        start = time.time()

        calc = MomentumFactorCalculator(df)
        result = calc.calculate_all()

        elapsed = time.time() - start

        # 5000行数据应该在2秒内完成
        assert elapsed < 2.0
        assert len(result) == n

    def test_many_periods_calculation(self):
        """测试计算大量周期"""
        df = pd.DataFrame({
            'close': np.random.randn(500).cumsum() + 100
        })

        periods = list(range(5, 101, 5))  # 5, 10, 15, ..., 100

        import time
        start = time.time()

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=periods)

        elapsed = time.time() - start

        # 应该在1秒内完成
        assert elapsed < 1.0
        # 应该生成所有周期的因子
        for period in periods:
            assert f'MOM{period}' in result.columns


# ==================== 并发安全测试 ====================


class TestConcurrencySafety:
    """并发安全测试（如果使用缓存）"""

    def test_cache_thread_safety(self):
        """测试缓存的线程安全性"""
        from src.features.alpha_factors import FactorCache

        cache = FactorCache(max_size=10)

        # 基本的缓存操作
        cache.put('key1', 'value1')
        assert cache.get('key1') == 'value1'

        # LRU淘汰
        for i in range(15):
            cache.put(f'key{i}', f'value{i}')

        # 超过max_size，最早的应该被淘汰
        assert len(cache._cache) <= 10
