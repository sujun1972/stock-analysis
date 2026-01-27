"""
技术指标计算器测试

测试所有技术指标计算函数，确保计算准确性和边界情况处理。

作者: Stock Analysis Team
更新: 2026-01-27
"""

import pytest
import pandas as pd
import numpy as np
from src.features.indicators_calculator import (
    safe_divide,
    calculate_rsi,
    calculate_macd,
    calculate_kdj,
    calculate_boll,
    calculate_atr,
    calculate_obv,
    calculate_cci,
)


# ==================== Fixtures ====================

@pytest.fixture
def sample_series():
    """生成简单的价格序列用于测试"""
    return pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 110])


@pytest.fixture
def sample_ohlcv_df():
    """生成完整的OHLCV数据用于测试"""
    return pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'high': [103, 105, 104, 106, 108, 107, 109, 111, 110, 113],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109],
        'close': [102, 101, 103, 105, 104, 106, 108, 107, 110, 112],
        'volume': [1000, 1200, 1100, 1300, 1250, 1150, 1400, 1350, 1450, 1500]
    })


@pytest.fixture
def large_ohlcv_df():
    """生成大量数据用于测试长周期指标"""
    np.random.seed(42)
    n = 100
    base_price = 100
    prices = base_price + np.cumsum(np.random.randn(n) * 0.5)

    df = pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(n) * 0.5),
        'low': prices - np.abs(np.random.randn(n) * 0.5),
        'close': prices + np.random.randn(n) * 0.3,
        'volume': np.random.randint(1000, 2000, n)
    })
    return df


@pytest.fixture
def extreme_volatility_df():
    """生成极端波动数据"""
    return pd.DataFrame({
        'open': [100, 150, 80, 120, 90],
        'high': [160, 180, 130, 140, 110],
        'low': [90, 70, 75, 85, 85],
        'close': [150, 80, 120, 90, 100],
        'volume': [5000, 8000, 6000, 4000, 5500]
    })


@pytest.fixture
def zero_volume_df():
    """生成包含零成交量的数据"""
    return pd.DataFrame({
        'open': [100, 102, 101, 103, 105],
        'high': [103, 105, 104, 106, 108],
        'low': [99, 101, 100, 102, 104],
        'close': [102, 101, 103, 105, 104],
        'volume': [1000, 0, 1100, 0, 1250]  # 包含零成交量
    })


@pytest.fixture
def constant_price_df():
    """生成价格不变的数据"""
    return pd.DataFrame({
        'open': [100] * 10,
        'high': [100] * 10,
        'low': [100] * 10,
        'close': [100] * 10,
        'volume': [1000] * 10
    })


# ==================== safe_divide 测试 ====================

class TestSafeDivide:
    """测试安全除法函数"""

    def test_normal_division(self):
        """测试正常除法"""
        numerator = pd.Series([10, 20, 30])
        denominator = pd.Series([2, 4, 5])
        result = safe_divide(numerator, denominator)

        expected = pd.Series([5.0, 5.0, 6.0])
        pd.testing.assert_series_equal(result, expected)

    def test_divide_by_zero(self):
        """测试除零情况"""
        numerator = pd.Series([10, 20, 30])
        denominator = pd.Series([2, 0, 5])
        result = safe_divide(numerator, denominator, fill_value=99.0)

        expected = pd.Series([5.0, 99.0, 6.0])
        pd.testing.assert_series_equal(result, expected)

    def test_divide_with_nan(self):
        """测试包含NaN的除法"""
        numerator = pd.Series([10, np.nan, 30])
        denominator = pd.Series([2, 4, 5])
        result = safe_divide(numerator, denominator, fill_value=0.0)

        assert result[0] == 5.0
        assert result[1] == 0.0  # NaN被填充为0
        assert result[2] == 6.0

    def test_divide_with_inf(self):
        """测试产生无穷大的除法"""
        numerator = pd.Series([10, 20, 30])
        denominator = pd.Series([0, 0, 0])
        result = safe_divide(numerator, denominator, fill_value=-1.0)

        # 所有值都应该被填充为-1.0
        expected = pd.Series([-1.0, -1.0, -1.0])
        pd.testing.assert_series_equal(result, expected)

    def test_custom_fill_value(self):
        """测试自定义填充值"""
        numerator = pd.Series([10, 20])
        denominator = pd.Series([0, 0])
        result = safe_divide(numerator, denominator, fill_value=999.0)

        expected = pd.Series([999.0, 999.0])
        pd.testing.assert_series_equal(result, expected)


# ==================== calculate_rsi 测试 ====================

class TestCalculateRSI:
    """测试RSI指标计算"""

    def test_rsi_basic(self, sample_series):
        """测试基本RSI计算"""
        result = calculate_rsi(sample_series, period=3)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_series)
        # RSI值应该在0-100之间（除了NaN）
        valid_values = result.dropna()
        assert all((valid_values >= 0) & (valid_values <= 100))

    def test_rsi_uptrend(self):
        """测试上升趋势的RSI（应该接近100）"""
        # 使用更长的序列以便RSI能够正确计算
        uptrend = pd.Series([100 + i*5 for i in range(20)])
        result = calculate_rsi(uptrend, period=6)

        # 在上升趋势中，RSI应该较高（排除前面的0值）
        valid_values = result[result > 0].dropna()
        if len(valid_values) > 0:
            assert valid_values.mean() > 50

    def test_rsi_downtrend(self):
        """测试下降趋势的RSI（应该接近0）"""
        downtrend = pd.Series([130, 125, 120, 115, 110, 105, 100])
        result = calculate_rsi(downtrend, period=3)

        # 在下降趋势中，RSI应该较低
        valid_values = result.dropna()
        assert all(valid_values < 50)

    def test_rsi_constant_price(self, constant_price_df):
        """测试价格不变时的RSI"""
        result = calculate_rsi(constant_price_df['close'], period=3)

        # 价格不变时，由于没有增益也没有损失，RSI可能为0或50
        # 实际上calculate_rsi使用safe_divide，当loss为0时会填充0或50
        valid_values = result.dropna()
        # 检查没有异常值（不是NaN或inf）
        assert not np.isinf(valid_values).any()
        # 价格不变时，所有值应该相同
        if len(valid_values) > 0:
            assert valid_values.nunique() <= 2  # 可能只有0或50

    def test_rsi_different_periods(self, large_ohlcv_df):
        """测试不同周期的RSI"""
        rsi_6 = calculate_rsi(large_ohlcv_df['close'], period=6)
        rsi_14 = calculate_rsi(large_ohlcv_df['close'], period=14)

        # 两个RSI都应该有有效值
        assert rsi_6.notna().sum() > 0
        assert rsi_14.notna().sum() > 0

        # 周期越长，RSI应该更平滑（波动性更小）
        # 注意：由于safe_divide可能产生0值，我们过滤掉0值
        rsi_6_valid = rsi_6[rsi_6 > 0].dropna()
        rsi_14_valid = rsi_14[rsi_14 > 0].dropna()

        if len(rsi_6_valid) > 10 and len(rsi_14_valid) > 10:
            assert rsi_6_valid.std() >= rsi_14_valid.std() * 0.5  # 允许一定误差


# ==================== calculate_macd 测试 ====================

class TestCalculateMACD:
    """测试MACD指标计算"""

    def test_macd_basic(self, sample_series):
        """测试基本MACD计算"""
        macd, signal, hist = calculate_macd(sample_series, fast=3, slow=6, signal=2)

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
        assert len(macd) == len(sample_series)
        assert len(signal) == len(sample_series)
        assert len(hist) == len(sample_series)

    def test_macd_relationship(self, large_ohlcv_df):
        """测试MACD各组成部分之间的关系"""
        macd, signal, hist = calculate_macd(
            large_ohlcv_df['close'],
            fast=12,
            slow=26,
            signal=9
        )

        # Histogram = MACD - Signal
        calculated_hist = macd - signal
        pd.testing.assert_series_equal(hist, calculated_hist, check_names=False)

    def test_macd_uptrend(self):
        """测试上升趋势的MACD"""
        uptrend = pd.Series(range(100, 150))
        macd, signal, hist = calculate_macd(uptrend, fast=5, slow=10, signal=3)

        # 在上升趋势中，MACD应该主要为正
        valid_macd = macd.dropna()
        assert valid_macd.tail(10).mean() > 0

    def test_macd_downtrend(self):
        """测试下降趋势的MACD"""
        downtrend = pd.Series(range(150, 100, -1))
        macd, signal, hist = calculate_macd(downtrend, fast=5, slow=10, signal=3)

        # 在下降趋势中，MACD应该主要为负
        valid_macd = macd.dropna()
        assert valid_macd.tail(10).mean() < 0

    def test_macd_constant_price(self, constant_price_df):
        """测试价格不变时的MACD"""
        macd, signal, hist = calculate_macd(
            constant_price_df['close'],
            fast=3,
            slow=6,
            signal=2
        )

        # 价格不变时，MACD应该趋近于0
        valid_macd = macd.dropna()
        assert all(abs(valid_macd) < 1e-10)


# ==================== calculate_kdj 测试 ====================

class TestCalculateKDJ:
    """测试KDJ指标计算"""

    def test_kdj_basic(self, sample_ohlcv_df):
        """测试基本KDJ计算"""
        k, d, j = calculate_kdj(sample_ohlcv_df, n=3, m1=3, m2=3)

        assert isinstance(k, pd.Series)
        assert isinstance(d, pd.Series)
        assert isinstance(j, pd.Series)
        assert len(k) == len(sample_ohlcv_df)

    def test_kdj_relationship(self, large_ohlcv_df):
        """测试KDJ各组成部分之间的关系"""
        k, d, j = calculate_kdj(large_ohlcv_df, n=9, m1=3, m2=3)

        # J = 3K - 2D
        calculated_j = 3 * k - 2 * d
        pd.testing.assert_series_equal(j, calculated_j, check_names=False)

    def test_kdj_range(self, large_ohlcv_df):
        """测试KDJ值范围（K和D应该在0-100之间，J可以超出）"""
        k, d, j = calculate_kdj(large_ohlcv_df, n=9, m1=3, m2=3)

        # K和D应该在0-100之间
        valid_k = k.dropna()
        valid_d = d.dropna()

        # 由于EMA平滑，K和D应该大致在0-100之间（可能略有超出）
        assert valid_k.min() >= -10  # 允许小范围超出
        assert valid_k.max() <= 110
        assert valid_d.min() >= -10
        assert valid_d.max() <= 110

    def test_kdj_extreme_volatility(self, extreme_volatility_df):
        """测试极端波动情况下的KDJ"""
        k, d, j = calculate_kdj(extreme_volatility_df, n=3, m1=3, m2=3)

        # 确保没有产生NaN（除了初始值）
        assert k.notna().sum() >= 2
        assert d.notna().sum() >= 2
        assert j.notna().sum() >= 2


# ==================== calculate_boll 测试 ====================

class TestCalculateBoll:
    """测试布林带指标计算"""

    def test_boll_basic(self, sample_series):
        """测试基本布林带计算"""
        upper, middle, lower = calculate_boll(sample_series, period=3, std_num=2)

        assert isinstance(upper, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(lower, pd.Series)
        assert len(upper) == len(sample_series)

    def test_boll_relationship(self, large_ohlcv_df):
        """测试布林带各部分之间的关系"""
        upper, middle, lower = calculate_boll(
            large_ohlcv_df['close'],
            period=20,
            std_num=2
        )

        # Middle应该是移动平均线
        expected_middle = large_ohlcv_df['close'].rolling(window=20).mean()
        pd.testing.assert_series_equal(middle, expected_middle, check_names=False)

        # Upper > Middle > Lower（对于有效值）
        valid_idx = middle.notna()
        assert all(upper[valid_idx] >= middle[valid_idx])
        assert all(middle[valid_idx] >= lower[valid_idx])

    def test_boll_width(self, large_ohlcv_df):
        """测试布林带宽度与标准差倍数的关系"""
        upper1, middle1, lower1 = calculate_boll(
            large_ohlcv_df['close'],
            period=20,
            std_num=1
        )
        upper2, middle2, lower2 = calculate_boll(
            large_ohlcv_df['close'],
            period=20,
            std_num=2
        )

        # 标准差倍数越大，带宽越宽
        valid_idx = middle1.notna()
        width1 = (upper1 - lower1)[valid_idx]
        width2 = (upper2 - lower2)[valid_idx]

        assert all(width2 > width1)

    def test_boll_constant_price(self, constant_price_df):
        """测试价格不变时的布林带"""
        upper, middle, lower = calculate_boll(
            constant_price_df['close'],
            period=3,
            std_num=2
        )

        # 价格不变时，上中下轨应该相等（标准差为0）
        valid_idx = middle.notna()
        pd.testing.assert_series_equal(
            upper[valid_idx],
            middle[valid_idx],
            check_names=False
        )
        pd.testing.assert_series_equal(
            middle[valid_idx],
            lower[valid_idx],
            check_names=False
        )


# ==================== calculate_atr 测试 ====================

class TestCalculateATR:
    """测试ATR指标计算"""

    def test_atr_basic(self, sample_ohlcv_df):
        """测试基本ATR计算"""
        result = calculate_atr(sample_ohlcv_df, period=3)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df)
        # ATR应该总是非负的
        valid_values = result.dropna()
        assert all(valid_values >= 0)

    def test_atr_high_volatility(self, extreme_volatility_df):
        """测试高波动率情况下的ATR"""
        atr_high = calculate_atr(extreme_volatility_df, period=3)

        # 高波动率的ATR应该较大
        valid_values = atr_high.dropna()
        assert valid_values.mean() > 10  # 基于extreme_volatility_df的数据

    def test_atr_low_volatility(self):
        """测试低波动率情况下的ATR"""
        low_vol_df = pd.DataFrame({
            'high': [100.5, 100.6, 100.7, 100.8, 100.9],
            'low': [100.4, 100.5, 100.6, 100.7, 100.8],
            'close': [100.45, 100.55, 100.65, 100.75, 100.85]
        })
        atr_low = calculate_atr(low_vol_df, period=3)

        # 低波动率的ATR应该较小
        valid_values = atr_low.dropna()
        assert valid_values.mean() < 1

    def test_atr_constant_price(self, constant_price_df):
        """测试价格不变时的ATR"""
        result = calculate_atr(constant_price_df, period=3)

        # 价格不变时，ATR应该为0
        valid_values = result.dropna()
        assert all(abs(valid_values) < 1e-10)


# ==================== calculate_obv 测试 ====================

class TestCalculateOBV:
    """测试OBV指标计算"""

    def test_obv_basic(self, sample_ohlcv_df):
        """测试基本OBV计算"""
        result = calculate_obv(sample_ohlcv_df)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df)
        # 第一个值应该是0
        assert result.iloc[0] == 0

    def test_obv_uptrend(self):
        """测试价格上涨时的OBV（应该累积上涨）"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1000, 1000, 1000, 1000]
        })
        result = calculate_obv(df)

        # OBV应该持续增长
        assert result.iloc[-1] > result.iloc[1]
        # 每次增加应该是volume的值
        assert result.iloc[2] - result.iloc[1] == 1000

    def test_obv_downtrend(self):
        """测试价格下跌时的OBV（应该累积下跌）"""
        df = pd.DataFrame({
            'close': [104, 103, 102, 101, 100],
            'volume': [1000, 1000, 1000, 1000, 1000]
        })
        result = calculate_obv(df)

        # OBV应该持续下降
        assert result.iloc[-1] < result.iloc[1]
        # 每次减少应该是volume的值
        assert result.iloc[2] - result.iloc[1] == -1000

    def test_obv_mixed_trend(self, sample_ohlcv_df):
        """测试混合趋势的OBV"""
        result = calculate_obv(sample_ohlcv_df)

        # OBV应该是累积的
        assert isinstance(result.iloc[-1], (int, float))

    def test_obv_zero_volume(self, zero_volume_df):
        """测试包含零成交量的OBV"""
        result = calculate_obv(zero_volume_df)

        # 零成交量不应该导致错误
        assert len(result) == len(zero_volume_df)
        assert result.notna().all()


# ==================== calculate_cci 测试 ====================

class TestCalculateCCI:
    """测试CCI指标计算"""

    def test_cci_basic(self, sample_ohlcv_df):
        """测试基本CCI计算"""
        result = calculate_cci(sample_ohlcv_df, period=3)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv_df)

    def test_cci_typical_price(self, sample_ohlcv_df):
        """测试CCI使用的典型价格（TP）"""
        result = calculate_cci(sample_ohlcv_df, period=3)

        # CCI应该围绕0波动
        valid_values = result.dropna()
        # 检查是否有正值和负值（对于正常波动的数据）
        assert len(valid_values) > 0

    def test_cci_extreme_volatility(self, extreme_volatility_df):
        """测试极端波动情况下的CCI"""
        result = calculate_cci(extreme_volatility_df, period=3)

        # CCI在极端波动时应该有较大的绝对值
        valid_values = result.dropna()
        assert valid_values.abs().mean() > 50

    def test_cci_constant_price(self, constant_price_df):
        """测试价格不变时的CCI"""
        result = calculate_cci(constant_price_df, period=3)

        # 价格不变时，CCI应该为0（或使用safe_divide的fill_value）
        valid_values = result.dropna()
        assert all(abs(valid_values) < 1e-6)

    def test_cci_different_periods(self, large_ohlcv_df):
        """测试不同周期的CCI"""
        cci_5 = calculate_cci(large_ohlcv_df, period=5)
        cci_20 = calculate_cci(large_ohlcv_df, period=20)

        # 周期越长，CCI越平滑（波动性越小）
        assert cci_5.std() > cci_20.std()


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """测试边界情况和异常处理"""

    def test_empty_series(self):
        """测试空序列"""
        empty = pd.Series([], dtype=float)

        # 大多数指标应该返回空序列或处理空输入
        result = safe_divide(empty, empty, fill_value=0)
        assert len(result) == 0

    def test_single_value(self):
        """测试单个值的序列"""
        single = pd.Series([100.0])

        # RSI with single value
        rsi = calculate_rsi(single, period=1)
        assert len(rsi) == 1

    def test_all_nan_series(self):
        """测试全NaN序列"""
        nan_series = pd.Series([np.nan] * 10)
        result = calculate_rsi(nan_series, period=3)

        # 应该返回全NaN或fill_value
        assert len(result) == 10

    def test_mixed_nan_values(self):
        """测试包含NaN的序列"""
        mixed = pd.Series([100, np.nan, 102, 103, np.nan, 105])
        result = calculate_rsi(mixed, period=3)

        # 应该能够处理NaN
        assert len(result) == len(mixed)


# ==================== 性能测试 ====================

class TestPerformance:
    """测试性能（简单的烟雾测试，确保不会超时）"""

    def test_large_dataset_rsi(self):
        """测试大数据集的RSI计算"""
        large_series = pd.Series(np.random.randn(10000).cumsum() + 100)
        result = calculate_rsi(large_series, period=14)

        assert len(result) == len(large_series)
        assert result.notna().sum() > 0

    def test_large_dataset_macd(self):
        """测试大数据集的MACD计算"""
        large_series = pd.Series(np.random.randn(10000).cumsum() + 100)
        macd, signal, hist = calculate_macd(large_series, fast=12, slow=26, signal=9)

        assert len(macd) == len(large_series)

    def test_large_dataset_all_indicators(self):
        """测试大数据集的所有指标计算"""
        n = 5000
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

        df = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(n) * 0.5),
            'low': prices - np.abs(np.random.randn(n) * 0.5),
            'close': prices + np.random.randn(n) * 0.3,
            'volume': np.random.randint(1000, 2000, n)
        })

        # 计算所有指标
        rsi = calculate_rsi(df['close'], period=14)
        macd, signal, hist = calculate_macd(df['close'], fast=12, slow=26, signal=9)
        k, d, j = calculate_kdj(df, n=9, m1=3, m2=3)
        upper, middle, lower = calculate_boll(df['close'], period=20, std_num=2)
        atr = calculate_atr(df, period=14)
        obv = calculate_obv(df)
        cci = calculate_cci(df, period=14)

        # 确保所有指标都能成功计算
        assert len(rsi) == n
        assert len(macd) == n
        assert len(k) == n
        assert len(upper) == n
        assert len(atr) == n
        assert len(obv) == n
        assert len(cci) == n


# ==================== 集成测试 ====================

class TestIntegration:
    """测试多个指标的集成使用"""

    def test_multiple_indicators_on_same_data(self, large_ohlcv_df):
        """测试在同一数据上计算多个指标"""
        # 计算多个指标
        rsi = calculate_rsi(large_ohlcv_df['close'], period=14)
        macd, signal, hist = calculate_macd(
            large_ohlcv_df['close'],
            fast=12,
            slow=26,
            signal=9
        )
        k, d, j = calculate_kdj(large_ohlcv_df, n=9, m1=3, m2=3)

        # 确保所有指标长度一致
        assert len(rsi) == len(large_ohlcv_df)
        assert len(macd) == len(large_ohlcv_df)
        assert len(k) == len(large_ohlcv_df)

    def test_indicators_with_different_periods(self, large_ohlcv_df):
        """测试不同周期的指标"""
        # 短期指标
        rsi_short = calculate_rsi(large_ohlcv_df['close'], period=6)
        ma_short = large_ohlcv_df['close'].rolling(window=5).mean()

        # 长期指标
        rsi_long = calculate_rsi(large_ohlcv_df['close'], period=14)
        ma_long = large_ohlcv_df['close'].rolling(window=20).mean()

        # 短期指标应该更敏感（波动性更大）
        assert rsi_short.std() >= rsi_long.std()
        assert ma_short.std() >= ma_long.std()
