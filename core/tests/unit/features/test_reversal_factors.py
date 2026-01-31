"""
反转因子计算器专项测试

测试 ReversalFactorCalculator 的所有功能：
- 短期反转因子(REV)
- Z-score均值回归因子
- 隔夜反转因子
- 日内收益率
- 边界情况和异常处理

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np

from src.features.alpha_factors import (
    ReversalFactorCalculator,
    FactorConfig,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_ohlc_data():
    """生成包含OHLC的完整数据"""
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
        'vol': np.random.uniform(1000000, 10000000, 200)
    }, index=dates)


@pytest.fixture
def oscillating_data():
    """生成震荡数据（适合测试反转）"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 正弦波震荡
    prices = 100 + 10 * np.sin(np.linspace(0, 8*np.pi, 100))

    return pd.DataFrame({
        'open': prices * 0.99,
        'close': prices
    }, index=dates)


@pytest.fixture
def gap_up_data():
    """生成跳空高开数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    close_prices = np.linspace(100, 110, 50)
    # 每天开盘跳空高开1%
    open_prices = close_prices * 1.01

    return pd.DataFrame({
        'open': open_prices,
        'close': close_prices
    }, index=dates)


@pytest.fixture
def gap_down_data():
    """生成跳空低开数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    close_prices = np.linspace(100, 110, 50)
    # 每天开盘跳空低开1%
    open_prices = close_prices * 0.99

    return pd.DataFrame({
        'open': open_prices,
        'close': close_prices
    }, index=dates)


# ==================== 基础功能测试 ====================


class TestReversalFactorBasics:
    """测试反转因子计算器的基础功能"""

    def test_calculator_initialization(self, sample_ohlc_data):
        """测试计算器初始化"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        assert calc.df is not None
        assert len(calc.df) == 200
        assert 'close' in calc.df.columns

    def test_validation_missing_close(self):
        """测试缺少close列时抛出异常"""
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104]
        })

        with pytest.raises(ValueError, match="缺少必需的列: close"):
            ReversalFactorCalculator(df)

    def test_validation_with_close(self, sample_ohlc_data):
        """测试有close列时正常初始化"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        calc._validate_dataframe()  # 不应抛出异常


# ==================== 短期反转因子测试 ====================


class TestReversalFactors:
    """测试短期反转因子(REV)"""

    def test_rev_basic_single_period(self, sample_ohlc_data):
        """测试单周期反转因子计算"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # 检查列是否创建
        assert 'REV1' in result.columns

        # 检查第一行应该是NaN
        assert result['REV1'].iloc[0] == 0 or pd.isna(result['REV1'].iloc[0])

        # 检查后续值不全是NaN
        assert not result['REV1'].iloc[1:].isna().all()

    def test_rev_multiple_periods(self, sample_ohlc_data):
        """测试多周期反转因子"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        short_periods = [1, 3, 5]
        result = calc.add_reversal_factors(short_periods=short_periods, long_periods=[])

        # 检查所有周期的列都创建了
        for period in short_periods:
            assert f'REV{period}' in result.columns

    def test_rev_formula_correctness(self):
        """测试反转因子公式正确性"""
        df = pd.DataFrame({
            'close': [100, 105, 103, 108, 104]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # REV1应该是负的pct_change
        # 第2个值: -(105/100 - 1) * 100 = -5.0
        assert abs(result['REV1'].iloc[1] - (-5.0)) < 0.01

        # 第3个值: -(103/105 - 1) * 100 ≈ 1.905
        assert abs(result['REV1'].iloc[2] - 1.905) < 0.01

    def test_rev_opposite_to_momentum(self):
        """测试反转因子是动量的负值"""
        df = pd.DataFrame({
            'close': [100, 105, 110, 108, 115]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[2], long_periods=[])

        # 手动计算MOM2
        mom2 = df['close'].pct_change(2) * 100

        # REV2应该是MOM2的负值
        assert np.allclose(
            result['REV2'].dropna(),
            -mom2.dropna(),
            rtol=0.001
        )

    def test_rev_default_periods(self, sample_ohlc_data):
        """测试默认短期周期[1, 3, 5]"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_reversal_factors(long_periods=[])  # 只测试短期

        # 默认短期周期
        assert 'REV1' in result.columns
        assert 'REV3' in result.columns
        assert 'REV5' in result.columns


# ==================== Z-score因子测试 ====================


class TestZScoreFactors:
    """测试Z-score均值回归因子"""

    def test_zscore_basic(self, sample_ohlc_data):
        """测试基础Z-score计算"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_reversal_factors(short_periods=[], long_periods=[20])

        assert 'ZSCORE20' in result.columns
        # 前19行应该是NaN（索引从0开始）
        assert result['ZSCORE20'].iloc[:19].isna().all()

    def test_zscore_multiple_periods(self, sample_ohlc_data):
        """测试多周期Z-score"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        periods = [20, 60]
        result = calc.add_reversal_factors(short_periods=[], long_periods=periods)

        for period in periods:
            assert f'ZSCORE{period}' in result.columns

    def test_zscore_formula_correctness(self):
        """测试Z-score公式正确性"""
        # 创建简单数据方便验证
        prices = list(range(100, 125))  # 100到124的线性数据
        df = pd.DataFrame({'close': prices})

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[], long_periods=[10])

        # 手动计算第15个位置的ZSCORE10
        window_prices = prices[5:15]  # 索引5-14的10个数据
        ma = np.mean(window_prices)
        std = np.std(window_prices, ddof=1)  # pandas默认ddof=1
        current_price = prices[14]
        manual_zscore = (ma - current_price) / std

        calculated_zscore = result['ZSCORE10'].iloc[14]

        assert abs(manual_zscore - calculated_zscore) < 0.01

    def test_zscore_positive_when_below_ma(self):
        """测试价格低于均线时Z-score为正（买入信号）"""
        # 创建先高后低的数据
        prices = [110, 109, 108, 107, 106, 105, 104, 103, 102, 101,
                 100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90]
        df = pd.DataFrame({'close': prices})

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[], long_periods=[10])

        # 后期价格明显低于前期均值，Z-score应该为正
        assert result['ZSCORE10'].iloc[-1] > 0

    def test_zscore_negative_when_above_ma(self):
        """测试价格高于均线时Z-score为负（卖出信号）"""
        # 创建先低后高的数据
        prices = [90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
                 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
        df = pd.DataFrame({'close': prices})

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[], long_periods=[10])

        # 后期价格明显高于前期均值，Z-score应该为负
        assert result['ZSCORE10'].iloc[-1] < 0

    def test_zscore_default_periods(self, sample_ohlc_data):
        """测试默认长期周期"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_reversal_factors(short_periods=[])  # 只测试长期

        # 默认长期周期应该是 [20, 60]
        for period in FactorConfig.DEFAULT_MEDIUM_PERIODS:
            assert f'ZSCORE{period}' in result.columns


# ==================== 隔夜反转因子测试 ====================


class TestOvernightReversal:
    """测试隔夜反转因子"""

    def test_overnight_reversal_basic(self, sample_ohlc_data):
        """测试基础隔夜反转计算"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_overnight_reversal()

        # 检查生成的列
        assert 'OVERNIGHT_RET' in result.columns
        assert 'INTRADAY_RET' in result.columns
        assert 'OVERNIGHT_REV' in result.columns

        # 第一行隔夜收益应该是NaN（没有前一天）
        assert pd.isna(result['OVERNIGHT_RET'].iloc[0])

    def test_overnight_ret_formula(self):
        """测试隔夜收益率公式"""
        df = pd.DataFrame({
            'open': [102, 104, 103],
            'close': [100, 102, 105]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_overnight_reversal()

        # 第2个值的隔夜收益: (104 - 100) / 100 * 100 = 4.0
        assert abs(result['OVERNIGHT_RET'].iloc[1] - 4.0) < 0.01

        # 第3个值的隔夜收益: (103 - 102) / 102 * 100 ≈ 0.98
        assert abs(result['OVERNIGHT_RET'].iloc[2] - 0.98) < 0.01

    def test_intraday_ret_formula(self):
        """测试日内收益率公式"""
        df = pd.DataFrame({
            'open': [102, 104, 103],
            'close': [105, 102, 108]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_overnight_reversal()

        # 第1个值的日内收益: (105 - 102) / 102 * 100 ≈ 2.94
        assert abs(result['INTRADAY_RET'].iloc[0] - 2.94) < 0.01

        # 第2个值的日内收益: (102 - 104) / 104 * 100 ≈ -1.92
        assert abs(result['INTRADAY_RET'].iloc[1] - (-1.92)) < 0.01

    def test_overnight_rev_is_negative_of_ret(self, sample_ohlc_data):
        """测试隔夜反转是隔夜收益的负值"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.add_overnight_reversal()

        # OVERNIGHT_REV应该是OVERNIGHT_RET的负值
        assert np.allclose(
            result['OVERNIGHT_REV'].dropna(),
            -result['OVERNIGHT_RET'].dropna(),
            rtol=0.001
        )

    def test_gap_up_detection(self, gap_up_data):
        """测试跳空高开检测"""
        calc = ReversalFactorCalculator(gap_up_data.copy())
        result = calc.add_overnight_reversal()

        # 跳空高开时，OVERNIGHT_RET应该为正
        valid_overnight = result['OVERNIGHT_RET'].dropna()
        assert (valid_overnight > 0).all()

        # 反转信号应该为负（做空高开）
        valid_rev = result['OVERNIGHT_REV'].dropna()
        assert (valid_rev < 0).all()

    def test_gap_down_detection(self, gap_down_data):
        """测试跳空低开检测"""
        calc = ReversalFactorCalculator(gap_down_data.copy())
        result = calc.add_overnight_reversal()

        # 跳空低开时，OVERNIGHT_RET应该为负
        valid_overnight = result['OVERNIGHT_RET'].dropna()
        assert (valid_overnight < 0).all()

        # 反转信号应该为正（做多低开）
        valid_rev = result['OVERNIGHT_REV'].dropna()
        assert (valid_rev > 0).all()

    def test_overnight_missing_open_column(self):
        """测试缺少open列时的处理"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_overnight_reversal()

        # 应该不会崩溃，但也不会生成隔夜因子
        assert 'OVERNIGHT_RET' not in result.columns


# ==================== 综合测试 ====================


class TestReversalCalculateAll:
    """测试calculate_all方法"""

    def test_calculate_all_basic(self, sample_ohlc_data):
        """测试计算所有反转因子"""
        calc = ReversalFactorCalculator(sample_ohlc_data.copy())
        result = calc.calculate_all()

        # 检查所有类型的因子都生成了
        assert any('REV' in col for col in result.columns)
        assert any('ZSCORE' in col for col in result.columns)
        assert 'OVERNIGHT_RET' in result.columns
        assert 'INTRADAY_RET' in result.columns

    def test_calculate_all_without_open(self):
        """测试只有close列时calculate_all"""
        df = pd.DataFrame({
            'close': np.random.randn(100).cumsum() + 100
        })

        calc = ReversalFactorCalculator(df)
        result = calc.calculate_all()

        # 应该有短期反转和Z-score，但没有隔夜因子
        assert any('REV' in col for col in result.columns)
        assert any('ZSCORE' in col for col in result.columns)


# ==================== 边界情况测试 ====================


class TestReversalEdgeCases:
    """测试边界情况和异常处理"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({'close': [100]})
        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # 单行数据无法计算反转，应该是0或NaN
        assert result['REV1'].iloc[0] == 0 or pd.isna(result['REV1'].iloc[0])

    def test_two_row_data(self):
        """测试两行数据"""
        df = pd.DataFrame({'close': [100, 105]})
        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # REV1应该能计算第二行
        assert abs(result['REV1'].iloc[1] - (-5.0)) < 0.01

    def test_small_dataset_large_period(self):
        """测试数据集小于周期"""
        df = pd.DataFrame({'close': list(range(100, 110))})
        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[], long_periods=[20])

        # 应该全是NaN
        assert result['ZSCORE20'].isna().all()

    def test_all_nan_prices(self):
        """测试价格全为NaN"""
        df = pd.DataFrame({
            'close': [np.nan] * 30
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # 应该全是NaN或0
        assert result['REV1'].isna().all() or (result['REV1'] == 0).all()

    def test_constant_price(self):
        """测试价格不变"""
        df = pd.DataFrame({
            'close': [100] * 50
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[5], long_periods=[20])

        # 价格不变，REV应该是0
        valid_rev = result['REV5'].dropna()
        assert (valid_rev.abs() < 0.01).all()

        # Z-score在价格不变时应该是NaN（std=0）
        # 或者被safe_divide处理为0
        valid_zscore = result['ZSCORE20'].dropna()
        if len(valid_zscore) > 0:
            assert (valid_zscore.abs() < 0.01).all() or valid_zscore.isna().all()

    def test_zero_prices(self):
        """测试包含0价格"""
        df = pd.DataFrame({
            'open': [100, 101, 0, 103, 104],
            'close': [100, 101, 0, 103, 104]
        })

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[])

        # 应该能处理，不会崩溃
        assert 'REV1' in result.columns

    def test_extreme_volatility(self):
        """测试极端波动"""
        prices = [100]
        for i in range(1, 50):
            # 随机暴涨暴跌
            change = 2.0 if i % 2 == 0 else 0.5
            prices.append(prices[-1] * change)

        df = pd.DataFrame({'close': prices})
        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[10])

        # 应该能处理极端波动
        assert 'REV1' in result.columns
        assert 'ZSCORE10' in result.columns


# ==================== 性能测试 ====================


class TestReversalPerformance:
    """测试性能相关"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        dates = pd.date_range('2020-01-01', periods=1000, freq='D')
        df = pd.DataFrame({
            'open': np.random.randn(1000).cumsum() + 100,
            'close': np.random.randn(1000).cumsum() + 100
        }, index=dates)

        import time
        start = time.time()
        calc = ReversalFactorCalculator(df)
        result = calc.calculate_all()
        elapsed = time.time() - start

        # 应该在1秒内完成
        assert elapsed < 1.0
        assert len(result) == 1000


# ==================== 实际场景测试 ====================


class TestReversalRealWorldScenarios:
    """测试实际市场场景"""

    def test_mean_reversion_scenario(self):
        """测试均值回归场景"""
        # 模拟价格偏离后回归的情况
        prices = [100] * 20 + [120] * 10 + [105] * 20  # 突然上涨后回落
        df = pd.DataFrame({'close': prices})

        calc = ReversalFactorCalculator(df)
        result = calc.add_reversal_factors(short_periods=[], long_periods=[20])

        # 在价格120的时候，Z-score应该为负（偏离均线向上）
        zscore_at_peak = result['ZSCORE20'].iloc[25]
        if not pd.isna(zscore_at_peak):
            assert zscore_at_peak < 0

        # 回落到105后，Z-score应该更接近0
        zscore_after_reversion = result['ZSCORE20'].iloc[-5]
        if not pd.isna(zscore_after_reversion):
            assert abs(zscore_after_reversion) < abs(zscore_at_peak)

    def test_oscillation_scenario(self, oscillating_data):
        """测试震荡市场"""
        calc = ReversalFactorCalculator(oscillating_data.copy())
        result = calc.calculate_all()

        # 震荡市场中，反转因子应该频繁变号
        sign_changes = (result['REV1'].dropna().diff().abs() > 0).sum()
        assert sign_changes > len(result) * 0.3  # 至少30%的时候在变号
