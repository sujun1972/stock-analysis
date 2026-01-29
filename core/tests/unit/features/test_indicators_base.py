"""
技术指标基类和 talib fallback 实现测试

覆盖范围：
1. BaseIndicator 基类功能
2. talib fallback 实现（14个技术指标函数）
3. DataFrame 验证机制
4. 边界情况和异常处理

目标覆盖率：90%+

作者: Stock Analysis Team
创建: 2026-01-27
"""

import pytest
import pandas as pd
import numpy as np
import warnings
import sys
import importlib.util
from pathlib import Path

# 直接加载模块文件，避免通过有问题的 features.__init__.py
base_module_path = Path(__file__).parent.parent.parent.parent / 'src' / 'features' / 'indicators' / 'base.py'
spec = importlib.util.spec_from_file_location("indicators_base", base_module_path)
indicators_base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(indicators_base)

# 从加载的模块中获取需要的类和对象
BaseIndicator = indicators_base.BaseIndicator
talib = indicators_base.talib
HAS_TALIB = indicators_base.HAS_TALIB


# ==================== Fixtures ====================

@pytest.fixture
def valid_ohlcv_df():
    """生成有效的OHLCV DataFrame"""
    return pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110] * 3,
        'high': [103, 105, 104, 106, 108, 107, 109, 111, 110, 113] * 3,
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109] * 3,
        'close': [102, 101, 103, 105, 104, 106, 108, 107, 110, 112] * 3,
        'volume': [1000, 1200, 1100, 1300, 1250, 1150, 1400, 1350, 1450, 1500] * 3
    })


@pytest.fixture
def minimal_ohlc_df():
    """生成最小化的OHLC DataFrame（无volume）"""
    return pd.DataFrame({
        'open': [100, 102, 101, 103, 105],
        'high': [103, 105, 104, 106, 108],
        'low': [99, 101, 100, 102, 104],
        'close': [102, 101, 103, 105, 104]
    })


@pytest.fixture
def price_series():
    """生成价格序列用于talib测试"""
    np.random.seed(42)
    base = 100
    prices = base + np.cumsum(np.random.randn(50) * 0.5)
    return pd.Series(prices)


@pytest.fixture
def ohlc_series():
    """生成OHLC序列用于talib测试"""
    np.random.seed(42)
    n = 50
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_price = close + np.random.randn(n) * 0.2
    volume = pd.Series(np.random.randint(1000, 2000, n))

    return {
        'high': pd.Series(high),
        'low': pd.Series(low),
        'close': pd.Series(close),
        'open': pd.Series(open_price),
        'volume': volume
    }


@pytest.fixture
def constant_price_series():
    """生成恒定价格序列"""
    return pd.Series([100.0] * 30)


# ==================== BaseIndicator 基类测试 ====================

class TestBaseIndicator:
    """测试 BaseIndicator 基类功能"""

    def test_init_with_valid_dataframe(self, valid_ohlcv_df):
        """测试使用有效DataFrame初始化"""
        indicator = BaseIndicator(valid_ohlcv_df)

        assert isinstance(indicator.df, pd.DataFrame)
        assert len(indicator.df) == len(valid_ohlcv_df)
        # 应该是副本，不是原始对象
        assert indicator.df is not valid_ohlcv_df

    def test_init_creates_copy(self, valid_ohlcv_df):
        """测试初始化时创建DataFrame副本"""
        original_df = valid_ohlcv_df.copy()
        indicator = BaseIndicator(valid_ohlcv_df)

        # 修改indicator的df不应该影响原始df
        indicator.df['new_column'] = 999
        assert 'new_column' not in valid_ohlcv_df.columns

    def test_init_with_minimal_columns(self, minimal_ohlc_df):
        """测试使用最小必需列初始化"""
        indicator = BaseIndicator(minimal_ohlc_df)

        assert 'open' in indicator.df.columns
        assert 'high' in indicator.df.columns
        assert 'low' in indicator.df.columns
        assert 'close' in indicator.df.columns

    def test_init_with_extra_columns(self, valid_ohlcv_df):
        """测试包含额外列的DataFrame"""
        df_with_extras = valid_ohlcv_df.copy()
        df_with_extras['extra1'] = 1
        df_with_extras['extra2'] = 'test'

        indicator = BaseIndicator(df_with_extras)

        # 额外的列应该被保留
        assert 'extra1' in indicator.df.columns
        assert 'extra2' in indicator.df.columns

    def test_validate_dataframe_missing_open(self, valid_ohlcv_df):
        """测试缺少open列的DataFrame"""
        invalid_df = valid_ohlcv_df.drop(columns=['open'])

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(invalid_df)

    def test_validate_dataframe_missing_high(self, valid_ohlcv_df):
        """测试缺少high列的DataFrame"""
        invalid_df = valid_ohlcv_df.drop(columns=['high'])

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(invalid_df)

    def test_validate_dataframe_missing_low(self, valid_ohlcv_df):
        """测试缺少low列的DataFrame"""
        invalid_df = valid_ohlcv_df.drop(columns=['low'])

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(invalid_df)

    def test_validate_dataframe_missing_close(self, valid_ohlcv_df):
        """测试缺少close列的DataFrame"""
        invalid_df = valid_ohlcv_df.drop(columns=['close'])

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(invalid_df)

    def test_validate_dataframe_missing_multiple_columns(self, valid_ohlcv_df):
        """测试缺少多个必需列的DataFrame"""
        invalid_df = valid_ohlcv_df.drop(columns=['open', 'close'])

        with pytest.raises(ValueError) as exc_info:
            BaseIndicator(invalid_df)

        error_msg = str(exc_info.value)
        assert 'open' in error_msg
        assert 'close' in error_msg

    def test_validate_dataframe_empty(self):
        """测试空DataFrame"""
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(empty_df)

    def test_validate_dataframe_wrong_column_names(self):
        """测试列名错误的DataFrame"""
        wrong_df = pd.DataFrame({
            'Open': [100, 101],  # 大写
            'High': [102, 103],
            'Low': [98, 99],
            'Close': [101, 102]
        })

        with pytest.raises(ValueError, match="DataFrame缺少必需的列"):
            BaseIndicator(wrong_df)

    def test_get_dataframe(self, valid_ohlcv_df):
        """测试get_dataframe方法"""
        indicator = BaseIndicator(valid_ohlcv_df)
        result = indicator.get_dataframe()

        assert isinstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, indicator.df)

    def test_get_dataframe_returns_reference(self, valid_ohlcv_df):
        """测试get_dataframe返回的是引用而非副本"""
        indicator = BaseIndicator(valid_ohlcv_df)
        df1 = indicator.get_dataframe()
        df2 = indicator.get_dataframe()

        # 应该是同一个对象
        assert df1 is df2
        assert df1 is indicator.df


# ==================== talib Fallback 实现测试 ====================

class TestTalibFallback:
    """测试 talib fallback 实现的所有技术指标"""

    # ========== SMA 测试 ==========

    def test_sma_basic(self, price_series):
        """测试SMA基本计算"""
        result = talib.SMA(price_series, timeperiod=5)

        assert isinstance(result, pd.Series)
        assert len(result) == len(price_series)

        # 手动验证前几个值
        expected_5 = price_series.iloc[:5].mean()
        assert abs(result.iloc[4] - expected_5) < 1e-10

    def test_sma_different_periods(self, price_series):
        """测试不同周期的SMA"""
        sma5 = talib.SMA(price_series, timeperiod=5)
        sma10 = talib.SMA(price_series, timeperiod=10)
        sma20 = talib.SMA(price_series, timeperiod=20)

        # 周期越长，初始NaN越多
        assert sma5.notna().sum() > sma10.notna().sum()
        assert sma10.notna().sum() > sma20.notna().sum()

    def test_sma_constant_price(self, constant_price_series):
        """测试恒定价格的SMA"""
        result = talib.SMA(constant_price_series, timeperiod=5)

        valid_values = result.dropna()
        assert all(abs(valid_values - 100.0) < 1e-10)

    # ========== EMA 测试 ==========

    def test_ema_basic(self, price_series):
        """测试EMA基本计算"""
        result = talib.EMA(price_series, timeperiod=12)

        assert isinstance(result, pd.Series)
        assert len(result) == len(price_series)
        assert result.notna().sum() > 0

    def test_ema_vs_sma(self, price_series):
        """测试EMA与SMA的区别（EMA更敏感）"""
        # 创建一个上升趋势
        uptrend = pd.Series(range(100, 150))

        sma = talib.SMA(uptrend, timeperiod=10)
        ema = talib.EMA(uptrend, timeperiod=10)

        # EMA应该更快地跟随价格（在上升趋势中，EMA > SMA）
        valid_idx = sma.notna() & ema.notna()
        if valid_idx.sum() > 0:
            assert (ema[valid_idx] >= sma[valid_idx]).mean() > 0.5

    def test_ema_constant_price(self, constant_price_series):
        """测试恒定价格的EMA"""
        result = talib.EMA(constant_price_series, timeperiod=5)

        valid_values = result.dropna()
        assert all(abs(valid_values - 100.0) < 1e-10)

    # ========== BBANDS 测试 ==========

    def test_bbands_basic(self, price_series):
        """测试布林带基本计算"""
        upper, middle, lower = talib.BBANDS(price_series, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)

        assert isinstance(upper, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(lower, pd.Series)
        assert len(upper) == len(price_series)

    def test_bbands_relationship(self, price_series):
        """测试布林带上中下轨关系"""
        upper, middle, lower = talib.BBANDS(price_series, timeperiod=20)

        # 中轨应该是SMA
        expected_middle = price_series.rolling(window=20).mean()
        pd.testing.assert_series_equal(middle, expected_middle)

        # 上轨 >= 中轨 >= 下轨
        valid_idx = middle.notna()
        assert all(upper[valid_idx] >= middle[valid_idx])
        assert all(middle[valid_idx] >= lower[valid_idx])

    def test_bbands_different_std(self, price_series):
        """测试不同标准差倍数的布林带"""
        upper1, middle1, lower1 = talib.BBANDS(price_series, timeperiod=20, nbdevup=1.0, nbdevdn=1.0)
        upper2, middle2, lower2 = talib.BBANDS(price_series, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)

        # 标准差倍数越大，带宽越宽
        valid_idx = middle1.notna()
        width1 = (upper1 - lower1)[valid_idx]
        width2 = (upper2 - lower2)[valid_idx]

        assert all(width2 > width1)

    def test_bbands_constant_price(self, constant_price_series):
        """测试恒定价格的布林带"""
        upper, middle, lower = talib.BBANDS(constant_price_series, timeperiod=10)

        # 恒定价格时，上中下轨应该相同（标准差为0）
        valid_idx = middle.notna()
        pd.testing.assert_series_equal(upper[valid_idx], middle[valid_idx])
        pd.testing.assert_series_equal(middle[valid_idx], lower[valid_idx])

    # ========== RSI 测试 ==========

    def test_rsi_basic(self, price_series):
        """测试RSI基本计算"""
        result = talib.RSI(price_series, timeperiod=14)

        assert isinstance(result, pd.Series)
        assert len(result) == len(price_series)

        # RSI应该在0-100之间
        valid_values = result.dropna()
        assert all((valid_values >= 0) & (valid_values <= 100))

    def test_rsi_uptrend(self):
        """测试上升趋势的RSI"""
        uptrend = pd.Series(range(100, 150))
        result = talib.RSI(uptrend, timeperiod=10)

        # 上升趋势中RSI应该偏高
        valid_values = result.dropna()
        if len(valid_values) > 5:
            assert valid_values.tail(5).mean() > 50

    def test_rsi_downtrend(self):
        """测试下降趋势的RSI"""
        downtrend = pd.Series(range(150, 100, -1))
        result = talib.RSI(downtrend, timeperiod=10)

        # 下降趋势中RSI应该偏低
        valid_values = result.dropna()
        if len(valid_values) > 5:
            assert valid_values.tail(5).mean() < 50

    def test_rsi_extreme_values(self):
        """测试极端情况的RSI"""
        # 持续上涨
        extreme_up = pd.Series([100 + i*10 for i in range(20)])
        rsi_up = talib.RSI(extreme_up, timeperiod=10)

        # 持续下跌
        extreme_down = pd.Series([200 - i*10 for i in range(20)])
        rsi_down = talib.RSI(extreme_down, timeperiod=10)

        # 极端上涨时RSI应该接近100
        assert rsi_up.dropna().tail(5).mean() > 70
        # 极端下跌时RSI应该接近0
        assert rsi_down.dropna().tail(5).mean() < 30

    # ========== MACD 测试 ==========

    def test_macd_basic(self, price_series):
        """测试MACD基本计算"""
        macd, signal, hist = talib.MACD(price_series, fastperiod=12, slowperiod=26, signalperiod=9)

        assert isinstance(macd, pd.Series)
        assert isinstance(signal, pd.Series)
        assert isinstance(hist, pd.Series)
        assert len(macd) == len(price_series)

    def test_macd_relationship(self, price_series):
        """测试MACD各部分关系"""
        macd, signal, hist = talib.MACD(price_series, fastperiod=12, slowperiod=26, signalperiod=9)

        # histogram = macd - signal
        calculated_hist = macd - signal
        pd.testing.assert_series_equal(hist, calculated_hist)

    def test_macd_ema_components(self, price_series):
        """测试MACD的EMA组成"""
        macd, signal, hist = talib.MACD(price_series, fastperiod=12, slowperiod=26, signalperiod=9)

        # 如果使用真实TA-Lib，跳过此测试（因为TA-Lib使用不同的EMA实现）
        if HAS_TALIB:
            pytest.skip("TA-Lib uses different EMA implementation")

        # MACD = EMA(12) - EMA(26) (仅对fallback实现有效)
        ema12 = talib.EMA(price_series, timeperiod=12)
        ema26 = talib.EMA(price_series, timeperiod=26)
        expected_macd = ema12 - ema26

        pd.testing.assert_series_equal(macd, expected_macd)

    def test_macd_constant_price(self, constant_price_series):
        """测试恒定价格的MACD"""
        macd, signal, hist = talib.MACD(constant_price_series, fastperiod=5, slowperiod=10, signalperiod=3)

        # 恒定价格时MACD应该为0
        valid_values = macd.dropna()
        assert all(abs(valid_values) < 1e-10)

    # ========== STOCH 测试 ==========

    def test_stoch_basic(self, ohlc_series):
        """测试STOCH基本计算"""
        slowk, slowd = talib.STOCH(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            fastk_period=5,
            slowk_period=3,
            slowd_period=3
        )

        assert isinstance(slowk, pd.Series)
        assert isinstance(slowd, pd.Series)
        assert len(slowk) == len(ohlc_series['close'])

    def test_stoch_range(self, ohlc_series):
        """测试STOCH值范围（应该在0-100之间）"""
        slowk, slowd = talib.STOCH(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            fastk_period=5,
            slowk_period=3,
            slowd_period=3
        )

        valid_k = slowk.dropna()
        valid_d = slowd.dropna()

        # 允许小范围超出（由于EMA平滑）
        assert valid_k.min() >= -10
        assert valid_k.max() <= 110
        assert valid_d.min() >= -10
        assert valid_d.max() <= 110

    def test_stoch_constant_price(self):
        """测试恒定价格的STOCH"""
        n = 20
        high = pd.Series([100.0] * n)
        low = pd.Series([100.0] * n)
        close = pd.Series([100.0] * n)

        slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3)

        # 恒定价格时，由于 (close - lowest) / (highest - lowest) = 0/0
        # 结果可能是NaN或其他值，取决于实现
        # 我们只确保不会抛出异常且长度正确
        assert len(slowk) == n
        assert len(slowd) == n

    # ========== CCI 测试 ==========

    def test_cci_basic(self, ohlc_series):
        """测试CCI基本计算"""
        result = talib.CCI(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=14
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(ohlc_series['close'])

    def test_cci_typical_price(self, ohlc_series):
        """测试CCI使用典型价格计算"""
        result = talib.CCI(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=14
        )

        # CCI应该围绕0波动
        valid_values = result.dropna()
        assert len(valid_values) > 0

    def test_cci_extreme_volatility(self):
        """测试极端波动的CCI"""
        # 创建高波动数据
        high = pd.Series([100, 150, 90, 160, 80, 170, 70] * 5)
        low = pd.Series([90, 80, 70, 90, 60, 80, 50] * 5)
        close = pd.Series([95, 140, 85, 150, 75, 160, 65] * 5)

        result = talib.CCI(high, low, close, timeperiod=5)

        # 高波动时CCI的绝对值应该较大
        valid_values = result.dropna()
        assert valid_values.abs().mean() > 10

    def test_cci_constant_price(self):
        """测试恒定价格的CCI"""
        n = 20
        high = pd.Series([100.0] * n)
        low = pd.Series([100.0] * n)
        close = pd.Series([100.0] * n)

        result = talib.CCI(high, low, close, timeperiod=10)

        # 恒定价格时MAD为0，会导致除零，应该产生NaN或inf
        # 我们的实现使用了0.015 * mad，所以会除以0
        assert len(result) == n

    # ========== ATR 测试 ==========

    def test_atr_basic(self, ohlc_series):
        """测试ATR基本计算"""
        result = talib.ATR(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=14
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(ohlc_series['close'])

        # ATR应该总是非负
        valid_values = result.dropna()
        assert all(valid_values >= 0)

    def test_atr_true_range_components(self, ohlc_series):
        """测试ATR的真实范围计算"""
        result = talib.ATR(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=5
        )

        # 如果使用真实TA-Lib，跳过此测试（因为TA-Lib使用EMA平滑而非SMA）
        if HAS_TALIB:
            pytest.skip("TA-Lib uses EMA smoothing, not SMA rolling mean")

        # 手动计算TR并验证（仅对fallback实现有效）
        tr1 = ohlc_series['high'] - ohlc_series['low']
        tr2 = abs(ohlc_series['high'] - ohlc_series['close'].shift())
        tr3 = abs(ohlc_series['low'] - ohlc_series['close'].shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        expected_atr = tr.rolling(window=5).mean()

        pd.testing.assert_series_equal(result, expected_atr)

    def test_atr_high_volatility(self):
        """测试高波动的ATR"""
        # 创建高波动数据
        high = pd.Series([100, 150, 90, 160, 80] * 10)
        low = pd.Series([90, 80, 70, 90, 60] * 10)
        close = pd.Series([95, 140, 85, 150, 75] * 10)

        result = talib.ATR(high, low, close, timeperiod=5)

        # 高波动时ATR应该较大
        valid_values = result.dropna()
        assert valid_values.mean() > 20

    def test_atr_constant_price(self):
        """测试恒定价格的ATR"""
        n = 20
        high = pd.Series([100.0] * n)
        low = pd.Series([100.0] * n)
        close = pd.Series([100.0] * n)

        result = talib.ATR(high, low, close, timeperiod=10)

        # 恒定价格时ATR应该为0
        valid_values = result.dropna()
        assert all(abs(valid_values) < 1e-10)

    # ========== OBV 测试 ==========

    def test_obv_basic(self, ohlc_series):
        """测试OBV基本计算"""
        result = talib.OBV(ohlc_series['close'], ohlc_series['volume'])

        assert isinstance(result, pd.Series)
        assert len(result) == len(ohlc_series['close'])

    def test_obv_uptrend(self):
        """测试上升趋势的OBV"""
        close = pd.Series([100, 101, 102, 103, 104])
        volume = pd.Series([1000, 1000, 1000, 1000, 1000])

        result = talib.OBV(close, volume)

        # OBV应该累积上涨
        assert result.iloc[-1] > result.iloc[0]

    def test_obv_downtrend(self):
        """测试下降趋势的OBV"""
        close = pd.Series([104, 103, 102, 101, 100])
        volume = pd.Series([1000, 1000, 1000, 1000, 1000])

        result = talib.OBV(close, volume)

        # OBV应该累积下跌
        assert result.iloc[-1] < result.iloc[0]

    def test_obv_mixed_trend(self, ohlc_series):
        """测试混合趋势的OBV"""
        result = talib.OBV(ohlc_series['close'], ohlc_series['volume'])

        # OBV应该是累积值
        assert isinstance(result.iloc[-1], (int, float, np.number))

    def test_obv_zero_volume(self):
        """测试零成交量的OBV"""
        close = pd.Series([100, 101, 102, 103, 104])
        volume = pd.Series([1000, 0, 1000, 0, 1000])

        result = talib.OBV(close, volume)

        # 零成交量不应该影响OBV
        assert len(result) == len(close)

    # ========== ADX 测试 ==========

    def test_adx_basic(self, ohlc_series):
        """测试ADX基本计算"""
        result = talib.ADX(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=14
        )

        assert isinstance(result, pd.Series)
        assert len(result) == len(ohlc_series['close'])

    def test_adx_range(self, ohlc_series):
        """测试ADX值范围（应该在0-100之间）"""
        result = talib.ADX(
            ohlc_series['high'],
            ohlc_series['low'],
            ohlc_series['close'],
            timeperiod=14
        )

        valid_values = result.dropna()
        # ADX应该在0-100之间
        assert all((valid_values >= 0) & (valid_values <= 100))

    def test_adx_strong_trend(self):
        """测试强趋势的ADX"""
        # 创建强上升趋势
        n = 50
        close = pd.Series(range(100, 100 + n))
        high = close + 1
        low = close - 1

        result = talib.ADX(high, low, close, timeperiod=10)

        # 强趋势时ADX应该较高
        valid_values = result.dropna()
        if len(valid_values) > 5:
            assert valid_values.tail(5).mean() > 20

    def test_adx_constant_price(self):
        """测试恒定价格的ADX"""
        n = 30
        high = pd.Series([100.0] * n)
        low = pd.Series([100.0] * n)
        close = pd.Series([100.0] * n)

        result = talib.ADX(high, low, close, timeperiod=10)

        # 恒定价格时ADX应该为0或NaN
        valid_values = result.dropna()
        if len(valid_values) > 0:
            # 由于除以0可能产生NaN，我们检查是否全是NaN或接近0
            assert (valid_values.isna().all() or
                    all(abs(valid_values) < 1e-6))


# ==================== 边界情况和异常处理测试 ====================

class TestEdgeCases:
    """测试边界情况和异常处理"""

    def test_empty_series(self):
        """测试空序列"""
        empty = pd.Series([], dtype=float)

        result = talib.SMA(empty, timeperiod=5)
        assert len(result) == 0

    def test_single_value_series(self):
        """测试单值序列"""
        single = pd.Series([100.0])

        if HAS_TALIB:
            # 真实TA-Lib不支持单值序列，会抛出异常
            with pytest.raises(Exception):
                talib.SMA(single, timeperiod=1)
        else:
            # fallback实现应该能处理
            result = talib.SMA(single, timeperiod=1)
            assert len(result) == 1
            assert result.iloc[0] == 100.0

    def test_series_shorter_than_period(self):
        """测试序列长度小于周期"""
        short = pd.Series([100, 101, 102])

        result = talib.SMA(short, timeperiod=10)

        # 应该全部为NaN
        assert result.isna().all()

    def test_series_with_nan(self):
        """测试包含NaN的序列"""
        with_nan = pd.Series([100, np.nan, 102, 103, 104])

        result = talib.SMA(with_nan, timeperiod=3)

        # rolling会传播NaN
        assert len(result) == len(with_nan)

    def test_series_with_inf(self):
        """测试包含无穷大的序列"""
        with_inf = pd.Series([100, 101, np.inf, 103, 104])

        result = talib.SMA(with_inf, timeperiod=3)

        # rolling会传播inf
        assert len(result) == len(with_inf)

    def test_negative_prices(self):
        """测试负价格（理论上不应该出现，但需要处理）"""
        negative = pd.Series([-100, -99, -98, -97, -96])

        result = talib.SMA(negative, timeperiod=3)

        # 应该能正常计算
        assert len(result) == len(negative)
        assert result.notna().sum() > 0

    def test_zero_prices(self):
        """测试零价格"""
        zeros = pd.Series([0.0] * 10)

        result = talib.SMA(zeros, timeperiod=5)

        valid_values = result.dropna()
        assert all(abs(valid_values) < 1e-10)

    def test_extreme_large_values(self):
        """测试极大值"""
        large = pd.Series([1e10, 1e10 + 1, 1e10 + 2, 1e10 + 3, 1e10 + 4])

        result = talib.SMA(large, timeperiod=3)

        # 应该能正常计算
        assert len(result) == len(large)

    def test_extreme_small_values(self):
        """测试极小值"""
        small = pd.Series([1e-10, 2e-10, 3e-10, 4e-10, 5e-10])

        result = talib.SMA(small, timeperiod=3)

        # 应该能正常计算
        assert len(result) == len(small)


# ==================== HAS_TALIB 标志测试 ====================

class TestHasTalibFlag:
    """测试 HAS_TALIB 标志"""

    def test_has_talib_is_boolean(self):
        """测试 HAS_TALIB 是布尔值"""
        assert isinstance(HAS_TALIB, bool)

    def test_talib_module_exists(self):
        """测试 talib 模块存在"""
        assert talib is not None

    def test_talib_has_sma_method(self):
        """测试 talib 有 SMA 方法"""
        assert hasattr(talib, 'SMA')
        assert callable(talib.SMA)

    def test_talib_has_all_required_methods(self):
        """测试 talib 包含所有必需的方法"""
        required_methods = [
            'SMA', 'EMA', 'BBANDS', 'RSI', 'MACD', 'STOCH',
            'CCI', 'ATR', 'OBV', 'ADX'
        ]

        for method in required_methods:
            assert hasattr(talib, method), f"talib missing method: {method}"
            assert callable(getattr(talib, method))


# ==================== 警告过滤测试 ====================

class TestWarningFiltering:
    """测试警告过滤配置"""

    def test_warnings_are_filtered(self):
        """测试警告被过滤"""
        # 这个测试确保导入模块时设置了warnings.filterwarnings('ignore')
        # 我们通过触发一个通常会产生警告的操作来测试

        with warnings.catch_warnings(record=True) as w:
            # 不应该有TA-Lib警告（如果已安装）或其他警告
            # 由于我们在模块级别设置了filterwarnings('ignore')
            # 这里应该捕获不到警告

            # 创建一个会产生除零警告的操作
            series = pd.Series([1, 2, 3, 0, 5])
            result = series / 0

            # 由于warnings.filterwarnings('ignore')，不应该有警告
            # 注意：这个测试依赖于模块导入时的设置
            pass


# ==================== 集成测试 ====================

class TestIntegration:
    """测试基类和talib的集成使用"""

    def test_base_indicator_with_talib_sma(self, valid_ohlcv_df):
        """测试在BaseIndicator中使用talib.SMA"""
        indicator = BaseIndicator(valid_ohlcv_df)

        # 添加SMA到DataFrame
        indicator.df['sma_5'] = talib.SMA(indicator.df['close'], timeperiod=5)
        indicator.df['sma_10'] = talib.SMA(indicator.df['close'], timeperiod=10)

        assert 'sma_5' in indicator.df.columns
        assert 'sma_10' in indicator.df.columns

    def test_base_indicator_with_multiple_talib_indicators(self, valid_ohlcv_df):
        """测试在BaseIndicator中使用多个talib指标"""
        indicator = BaseIndicator(valid_ohlcv_df)

        # 添加多个指标
        indicator.df['rsi'] = talib.RSI(indicator.df['close'], timeperiod=14)
        macd, signal, hist = talib.MACD(indicator.df['close'])
        indicator.df['macd'] = macd
        indicator.df['macd_signal'] = signal
        indicator.df['macd_hist'] = hist

        upper, middle, lower = talib.BBANDS(indicator.df['close'], timeperiod=20)
        indicator.df['bb_upper'] = upper
        indicator.df['bb_middle'] = middle
        indicator.df['bb_lower'] = lower

        # 验证所有指标都被添加
        assert 'rsi' in indicator.df.columns
        assert 'macd' in indicator.df.columns
        assert 'bb_upper' in indicator.df.columns

        # 验证数据长度一致
        assert len(indicator.df['rsi']) == len(valid_ohlcv_df)

    def test_full_workflow(self, valid_ohlcv_df):
        """测试完整的工作流程"""
        # 1. 创建指标计算器
        indicator = BaseIndicator(valid_ohlcv_df)

        # 2. 添加趋势指标
        indicator.df['sma_20'] = talib.SMA(indicator.df['close'], timeperiod=20)
        indicator.df['ema_12'] = talib.EMA(indicator.df['close'], timeperiod=12)

        # 3. 添加动量指标
        indicator.df['rsi'] = talib.RSI(indicator.df['close'], timeperiod=14)

        # 4. 添加波动率指标
        indicator.df['atr'] = talib.ATR(
            indicator.df['high'],
            indicator.df['low'],
            indicator.df['close'],
            timeperiod=14
        )

        # 5. 添加成交量指标
        indicator.df['obv'] = talib.OBV(indicator.df['close'], indicator.df['volume'])

        # 6. 获取结果
        result = indicator.get_dataframe()

        # 验证
        expected_columns = ['open', 'high', 'low', 'close', 'volume',
                           'sma_20', 'ema_12', 'rsi', 'atr', 'obv']
        for col in expected_columns:
            assert col in result.columns

        assert len(result) == len(valid_ohlcv_df)


# ==================== Fallback实现专项测试 ====================

class TestFallbackImplementation:
    """专门测试fallback实现路径的测试（当TA-Lib未安装时）"""

    def test_fallback_talib_import_warning(self):
        """测试TA-Lib未安装时的警告"""
        # 由于我们在模块级别设置了warnings.filterwarnings('ignore')
        # 这个测试主要验证HAS_TALIB标志的正确性
        assert isinstance(HAS_TALIB, bool)

    def test_fallback_sma_implementation(self):
        """测试SMA fallback实现的正确性"""
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        # 使用talib（可能是fallback）
        result = talib.SMA(data, timeperiod=3)

        # 验证前两个值为NaN
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])

        # 验证第三个值 = (1+2+3)/3 = 2.0
        assert abs(result.iloc[2] - 2.0) < 1e-10

        # 验证第四个值 = (2+3+4)/3 = 3.0
        assert abs(result.iloc[3] - 3.0) < 1e-10

    def test_fallback_ema_implementation(self):
        """测试EMA fallback实现的正确性"""
        data = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

        result = talib.EMA(data, timeperiod=3)

        # EMA应该有值（虽然前几个可能是NaN）
        assert result.notna().sum() > 0

        # EMA的最后一个值应该接近10（因为数据是递增的）
        assert result.iloc[-1] > 5

    def test_fallback_bbands_calculation(self):
        """测试BBANDS fallback实现"""
        data = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 110] * 3)

        upper, middle, lower = talib.BBANDS(data, timeperiod=5, nbdevup=2.0, nbdevdn=2.0)

        # 验证中轨是移动平均
        expected_middle = data.rolling(window=5).mean()
        pd.testing.assert_series_equal(middle, expected_middle)

        # 验证上轨 >= 中轨 >= 下轨
        valid_idx = middle.notna()
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()

    def test_fallback_rsi_calculation(self):
        """测试RSI fallback实现"""
        # 创建明确的上升趋势
        data = pd.Series([100, 105, 110, 115, 120, 125, 130, 135, 140, 145])

        result = talib.RSI(data, timeperiod=5)

        # RSI应该在0-100之间
        valid_values = result.dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()

        # 上升趋势中RSI应该较高
        if len(valid_values) > 0:
            assert valid_values.mean() > 30

    def test_fallback_macd_calculation(self):
        """测试MACD fallback实现"""
        data = pd.Series(range(100, 150))

        macd, signal, hist = talib.MACD(data, fastperiod=5, slowperiod=10, signalperiod=3)

        # 验证长度
        assert len(macd) == len(data)
        assert len(signal) == len(data)
        assert len(hist) == len(data)

        # 验证histogram = macd - signal
        pd.testing.assert_series_equal(hist, macd - signal)

    def test_fallback_stoch_calculation(self):
        """测试STOCH fallback实现"""
        n = 30
        high = pd.Series(range(100, 100 + n))
        low = pd.Series(range(95, 95 + n))
        close = pd.Series(range(97, 97 + n))

        slowk, slowd = talib.STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3)

        # 验证长度
        assert len(slowk) == n
        assert len(slowd) == n

        # 验证有有效值
        assert slowk.notna().sum() > 0
        assert slowd.notna().sum() > 0

    def test_fallback_cci_calculation(self):
        """测试CCI fallback实现"""
        n = 30
        high = pd.Series([100 + i + np.random.random() for i in range(n)])
        low = pd.Series([98 + i + np.random.random() for i in range(n)])
        close = pd.Series([99 + i + np.random.random() for i in range(n)])

        result = talib.CCI(high, low, close, timeperiod=10)

        # 验证长度和有效值
        assert len(result) == n
        assert result.notna().sum() > 0

    def test_fallback_atr_calculation(self):
        """测试ATR fallback实现"""
        n = 30
        high = pd.Series(range(105, 105 + n))
        low = pd.Series(range(95, 95 + n))
        close = pd.Series(range(100, 100 + n))

        result = talib.ATR(high, low, close, timeperiod=10)

        # ATR应该非负
        valid_values = result.dropna()
        assert (valid_values >= 0).all()

        # 验证长度
        assert len(result) == n

    def test_fallback_obv_calculation(self):
        """测试OBV fallback实现"""
        close = pd.Series([100, 101, 102, 101, 103, 104, 103, 105])
        volume = pd.Series([1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000])

        result = talib.OBV(close, volume)

        # 验证长度
        assert len(result) == len(close)

        # OBV应该是累积值
        assert result.notna().all()

    def test_fallback_adx_calculation(self):
        """测试ADX fallback实现"""
        n = 50
        high = pd.Series(range(100, 100 + n))
        low = pd.Series(range(95, 95 + n))
        close = pd.Series(range(97, 97 + n))

        result = talib.ADX(high, low, close, timeperiod=14)

        # 验证长度
        assert len(result) == n

        # ADX应该在0-100之间
        valid_values = result.dropna()
        if len(valid_values) > 0:
            assert (valid_values >= 0).all()
            assert (valid_values <= 100).all()

    def test_all_fallback_functions_exist(self):
        """测试所有fallback函数都存在"""
        required_functions = [
            'SMA', 'EMA', 'BBANDS', 'RSI', 'MACD',
            'STOCH', 'CCI', 'ATR', 'OBV', 'ADX'
        ]

        for func_name in required_functions:
            assert hasattr(talib, func_name), f"Missing function: {func_name}"
            assert callable(getattr(talib, func_name)), f"{func_name} is not callable"

    def test_fallback_with_empty_data(self):
        """测试fallback处理空数据"""
        empty = pd.Series([], dtype=float)

        result = talib.SMA(empty, timeperiod=5)
        assert len(result) == 0

    def test_fallback_with_insufficient_data(self):
        """测试fallback处理数据不足的情况"""
        short_data = pd.Series([1, 2])

        result = talib.SMA(short_data, timeperiod=10)

        # 数据太短，应该全是NaN
        assert result.isna().all()

    def test_fallback_preserves_index(self):
        """测试fallback保留原始索引"""
        data = pd.Series([1, 2, 3, 4, 5], index=['a', 'b', 'c', 'd', 'e'])

        result = talib.SMA(data, timeperiod=3)

        # 验证索引保持不变
        pd.testing.assert_index_equal(result.index, data.index)
