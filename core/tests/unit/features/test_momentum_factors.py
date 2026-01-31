"""
动量因子计算器专项测试

测试 MomentumFactorCalculator 的所有功能：
- 简单收益率动量(MOM)
- 对数收益率动量(MOM_LOG)
- 相对强度(RS)
- RSI相对强弱指标
- 加速度因子(ACC)
- 边界情况和异常处理

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np

from src.features.alpha_factors import (
    MomentumFactorCalculator,
    FactorConfig,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_price_data():
    """生成标准价格数据（300天）"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 300)
    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 300)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 300)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 300)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)


@pytest.fixture
def trending_up_data():
    """生成持续上涨的价格数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 持续上涨趋势
    prices = np.linspace(100, 200, 100)

    return pd.DataFrame({
        'close': prices
    }, index=dates)


@pytest.fixture
def trending_down_data():
    """生成持续下跌的价格数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 持续下跌趋势
    prices = np.linspace(200, 100, 100)

    return pd.DataFrame({
        'close': prices
    }, index=dates)


@pytest.fixture
def sideways_data():
    """生成横盘震荡的价格数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    # 围绕100波动
    prices = 100 + np.sin(np.linspace(0, 4*np.pi, 100)) * 5

    return pd.DataFrame({
        'close': prices
    }, index=dates)


@pytest.fixture
def small_dataset():
    """生成小数据集（测试边界）"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')

    return pd.DataFrame({
        'close': [100, 101, 102, 101, 103, 104, 103, 105, 106, 107]
    }, index=dates)


# ==================== 基础功能测试 ====================


class TestMomentumFactorBasics:
    """测试动量因子计算器的基础功能"""

    def test_calculator_initialization(self, sample_price_data):
        """测试计算器初始化"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        assert calc.df is not None
        assert len(calc.df) == 300
        assert 'close' in calc.df.columns

    def test_validation_missing_close(self):
        """测试缺少close列时抛出异常"""
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [102, 103, 104]
        })

        with pytest.raises(ValueError, match="缺少必需的列: close"):
            MomentumFactorCalculator(df)

    def test_validation_with_close(self, sample_price_data):
        """测试有close列时正常初始化"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        calc._validate_dataframe()  # 不应抛出异常


# ==================== MOM动量因子测试 ====================


class TestMomentumFactors:
    """测试简单收益率和对数收益率动量"""

    def test_mom_basic_single_period(self, sample_price_data):
        """测试单周期动量计算"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_momentum_factors(periods=[5])

        # 检查列是否创建
        assert 'MOM5' in result.columns
        assert 'MOM_LOG5' in result.columns

        # 检查前5行应该是NaN
        assert result['MOM5'].iloc[:5].isna().all()

        # 检查后续值不全是NaN
        assert not result['MOM5'].iloc[5:].isna().all()

    def test_mom_multiple_periods(self, sample_price_data):
        """测试多周期动量计算"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        periods = [5, 10, 20, 60, 120]
        result = calc.add_momentum_factors(periods=periods)

        # 检查所有周期的列都创建了
        for period in periods:
            assert f'MOM{period}' in result.columns
            assert f'MOM_LOG{period}' in result.columns

    def test_mom_formula_correctness(self, trending_up_data):
        """测试动量公式正确性"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_momentum_factors(periods=[10])

        # 手动计算第11个点的MOM10
        manual_mom = (trending_up_data['close'].iloc[10] /
                     trending_up_data['close'].iloc[0] - 1) * 100
        calculated_mom = result['MOM10'].iloc[10]

        assert abs(manual_mom - calculated_mom) < 0.01

    def test_mom_log_formula_correctness(self, trending_up_data):
        """测试对数收益率动量公式正确性"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_momentum_factors(periods=[10])

        # 手动计算对数收益率
        manual_mom_log = np.log(trending_up_data['close'].iloc[10] /
                                trending_up_data['close'].iloc[0]) * 100
        calculated_mom_log = result['MOM_LOG10'].iloc[10]

        assert abs(manual_mom_log - calculated_mom_log) < 0.01

    def test_mom_uptrend_positive(self, trending_up_data):
        """测试上涨趋势中动量为正"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_momentum_factors(periods=[20])

        # 上涨趋势中，除了前20个NaN，其余应该都是正值
        valid_mom = result['MOM20'].iloc[20:]
        assert (valid_mom > 0).all()

    def test_mom_downtrend_negative(self, trending_down_data):
        """测试下跌趋势中动量为负"""
        calc = MomentumFactorCalculator(trending_down_data.copy())
        result = calc.add_momentum_factors(periods=[20])

        # 下跌趋势中，除了前20个NaN，其余应该都是负值
        valid_mom = result['MOM20'].iloc[20:]
        assert (valid_mom < 0).all()

    def test_mom_default_periods(self, sample_price_data):
        """测试默认周期"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_momentum_factors()  # 不指定periods

        # 默认周期应该是 [5, 10, 20, 60, 120]
        expected_periods = FactorConfig.DEFAULT_SHORT_PERIODS + FactorConfig.DEFAULT_LONG_PERIODS
        for period in expected_periods:
            assert f'MOM{period}' in result.columns


# ==================== 相对强度(RS)测试 ====================


class TestRelativeStrength:
    """测试相对强度因子"""

    def test_rs_basic(self, sample_price_data):
        """测试基础相对强度计算"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_relative_strength(periods=[20])

        assert 'RS20' in result.columns
        # 前19行应该是NaN（需要20天计算均线）
        assert result['RS20'].iloc[:19].isna().all()

    def test_rs_multiple_periods(self, sample_price_data):
        """测试多周期相对强度"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        periods = [20, 60]
        result = calc.add_relative_strength(periods=periods)

        for period in periods:
            assert f'RS{period}' in result.columns

    def test_rs_formula_correctness(self, trending_up_data):
        """测试RS公式正确性"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_relative_strength(periods=[10])

        # 手动计算第20个点的RS10
        ma = trending_up_data['close'].iloc[:20].rolling(10).mean().iloc[-1]
        price = trending_up_data['close'].iloc[19]
        manual_rs = ((price - ma) / ma) * 100
        calculated_rs = result['RS10'].iloc[19]

        assert abs(manual_rs - calculated_rs) < 0.01

    def test_rs_above_ma_positive(self, trending_up_data):
        """测试价格在均线上方时RS为正"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_relative_strength(periods=[5])

        # 强上涨趋势中，价格应该在均线上方，RS应该为正
        valid_rs = result['RS5'].iloc[50:]  # 取中后段数据
        assert (valid_rs > 0).mean() > 0.7  # 至少70%为正

    def test_rs_default_periods(self, sample_price_data):
        """测试默认周期"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_relative_strength()  # 不指定periods

        # 默认周期应该是 [20, 60]
        for period in FactorConfig.DEFAULT_MEDIUM_PERIODS:
            assert f'RS{period}' in result.columns


# ==================== RSI测试 ====================


class TestRSI:
    """测试RSI相对强弱指标"""

    def test_rsi_basic(self, sample_price_data):
        """测试基础RSI计算"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_rsi(periods=[14])

        assert 'RSI14' in result.columns
        # 前14行应该是NaN
        assert result['RSI14'].iloc[:14].isna().all()

    def test_rsi_range_0_100(self, sample_price_data):
        """测试RSI值在0-100范围内"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_rsi(periods=[14])

        valid_rsi = result['RSI14'].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_uptrend_above_50(self, trending_up_data):
        """测试上涨趋势中RSI大于50"""
        calc = MomentumFactorCalculator(trending_up_data.copy())
        result = calc.add_rsi(periods=[14])

        valid_rsi = result['RSI14'].iloc[20:]  # 取稳定后的值
        assert valid_rsi.mean() > 50

    def test_rsi_downtrend_below_50(self, trending_down_data):
        """测试下跌趋势中RSI小于50"""
        calc = MomentumFactorCalculator(trending_down_data.copy())
        result = calc.add_rsi(periods=[14])

        valid_rsi = result['RSI14'].iloc[20:]
        assert valid_rsi.mean() < 50

    def test_rsi_multiple_periods(self, sample_price_data):
        """测试多周期RSI"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        periods = [14, 28]
        result = calc.add_rsi(periods=periods)

        for period in periods:
            assert f'RSI{period}' in result.columns

    def test_rsi_default_periods(self, sample_price_data):
        """测试默认周期[14, 28]"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_rsi()

        assert 'RSI14' in result.columns
        assert 'RSI28' in result.columns

    def test_rsi_constant_price(self):
        """测试价格不变时RSI为0或NaN"""
        df = pd.DataFrame({
            'close': [100] * 30  # 价格不变
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_rsi(periods=[14])

        # 价格不变时，涨跌都是0，RSI应该是0或NaN
        valid_rsi = result['RSI14'].dropna()
        if len(valid_rsi) > 0:
            # 如果有值，应该接近0（无变化）
            assert (valid_rsi.abs() < 1).all() or (valid_rsi == 0).all()


# ==================== 加速度因子测试 ====================


class TestAcceleration:
    """测试加速度因子"""

    def test_acc_basic(self, sample_price_data):
        """测试基础加速度计算"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_acceleration(periods=[5])

        assert 'ACC5' in result.columns
        # 前10行应该是NaN（需要两倍周期）
        assert result['ACC5'].iloc[:10].isna().all()

    def test_acc_multiple_periods(self, sample_price_data):
        """测试多周期加速度"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        periods = [5, 10, 20]
        result = calc.add_acceleration(periods=periods)

        for period in periods:
            assert f'ACC{period}' in result.columns

    def test_acc_positive_in_acceleration(self):
        """测试加速上涨时加速度为正"""
        # 创建加速上涨的数据：涨速越来越快
        prices = [100]
        for i in range(1, 50):
            # 涨幅逐渐增大
            growth_rate = 0.01 + i * 0.0001
            prices.append(prices[-1] * (1 + growth_rate))

        df = pd.DataFrame({'close': prices})
        calc = MomentumFactorCalculator(df)
        result = calc.add_acceleration(periods=[5])

        # 加速上涨时，加速度应该为正
        valid_acc = result['ACC5'].iloc[20:40]  # 取中间段
        assert (valid_acc > 0).mean() > 0.6  # 至少60%为正

    def test_acc_default_periods(self, sample_price_data):
        """测试默认周期"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_acceleration()

        for period in FactorConfig.DEFAULT_SHORT_PERIODS:
            assert f'ACC{period}' in result.columns


# ==================== 综合测试 ====================


class TestMomentumCalculateAll:
    """测试calculate_all方法"""

    def test_calculate_all_basic(self, sample_price_data):
        """测试计算所有动量因子"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.calculate_all()

        # 检查所有类型的因子都生成了
        assert any('MOM' in col for col in result.columns)
        assert any('RS' in col for col in result.columns)
        assert any('ACC' in col for col in result.columns)

    def test_calculate_all_no_modification(self, sample_price_data):
        """测试原始数据不被修改（如果传入副本）"""
        original = sample_price_data.copy()
        calc = MomentumFactorCalculator(sample_price_data.copy())
        calc.calculate_all()

        # 原始数据应该没有新增列
        assert set(original.columns) == set(sample_price_data.columns)


# ==================== 边界情况测试 ====================


class TestMomentumEdgeCases:
    """测试边界情况和异常处理"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({'close': [100]})
        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 单行数据无法计算动量，应该是NaN
        assert result['MOM5'].isna().all()

    def test_small_dataset_large_period(self, small_dataset):
        """测试数据集小于周期"""
        calc = MomentumFactorCalculator(small_dataset.copy())
        result = calc.add_momentum_factors(periods=[20])  # 周期20但只有10行数据

        # 应该全是NaN
        assert result['MOM20'].isna().all()

    def test_all_nan_prices(self):
        """测试价格全为NaN"""
        df = pd.DataFrame({
            'close': [np.nan] * 30
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 应该全是NaN
        assert result['MOM5'].isna().all()

    def test_some_nan_prices(self):
        """测试部分价格为NaN"""
        prices = [100, 101, np.nan, 103, 104, np.nan, 106] + list(range(107, 130))
        df = pd.DataFrame({'close': prices})

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 有些值应该是NaN，有些应该有值
        assert result['MOM5'].isna().sum() > 5
        assert result['MOM5'].notna().sum() > 0

    def test_zero_prices(self):
        """测试价格为0的情况"""
        df = pd.DataFrame({
            'close': [100, 101, 0, 103, 104] + list(range(105, 130))
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 应该能处理，不会崩溃
        assert 'MOM5' in result.columns

    def test_negative_prices(self):
        """测试负价格（理论上不应该出现但要防御）"""
        df = pd.DataFrame({
            'close': [100, 101, -50, 103, 104] + list(range(105, 130))
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 对数收益率在负价格时会产生NaN
        assert 'MOM_LOG5' in result.columns

    def test_constant_price(self):
        """测试价格不变"""
        df = pd.DataFrame({
            'close': [100] * 50
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 价格不变，动量应该是0
        valid_mom = result['MOM5'].dropna()
        assert (valid_mom.abs() < 0.01).all()  # 接近0

    def test_extreme_volatility(self):
        """测试极端波动"""
        prices = [100]
        for i in range(1, 50):
            # 随机暴涨暴跌
            change = 2.0 if i % 2 == 0 else 0.5
            prices.append(prices[-1] * change)

        df = pd.DataFrame({'close': prices})
        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        # 应该能处理极端波动，不会崩溃
        assert 'MOM5' in result.columns
        assert result['MOM5'].notna().sum() > 0


# ==================== 性能测试 ====================


class TestMomentumPerformance:
    """测试性能相关"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        # 生成1000天数据
        dates = pd.date_range('2020-01-01', periods=1000, freq='D')
        df = pd.DataFrame({
            'close': np.random.randn(1000).cumsum() + 100
        }, index=dates)

        import time
        start = time.time()
        calc = MomentumFactorCalculator(df)
        result = calc.calculate_all()
        elapsed = time.time() - start

        # 应该在1秒内完成
        assert elapsed < 1.0
        assert len(result) == 1000

    def test_cache_usage(self, sample_price_data):
        """测试缓存基础功能"""
        from src.features.alpha_factors import FactorCache

        cache = FactorCache(max_size=100)

        # 测试缓存的基本功能
        cache.put('test_key', 'test_value')
        assert cache.get('test_key') == 'test_value'

        # 测试LRU淘汰
        for i in range(105):
            cache.put(f'key{i}', f'value{i}')

        # 缓存大小不应超过max_size
        assert len(cache._cache) <= 100


# ==================== 数据类型测试 ====================


class TestMomentumDataTypes:
    """测试不同数据类型的处理"""

    def test_integer_prices(self):
        """测试整数价格"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110] * 3
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[5])

        assert 'MOM5' in result.columns
        assert result['MOM5'].dtype in [np.float64, float]

    def test_float_prices(self, sample_price_data):
        """测试浮点数价格"""
        calc = MomentumFactorCalculator(sample_price_data.copy())
        result = calc.add_momentum_factors(periods=[5])

        assert 'MOM5' in result.columns

    def test_custom_price_column(self):
        """测试自定义价格列"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104] * 5,
            'adj_close': [98, 99, 100, 101, 102] * 5
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[3], price_col='adj_close')

        # 应该基于adj_close计算
        assert 'MOM3' in result.columns


# ==================== 公式验证测试 ====================


class TestMomentumFormulaValidation:
    """详细验证计算公式的正确性"""

    def test_mom_vs_manual_calculation(self):
        """对比自动计算和手动计算的MOM"""
        df = pd.DataFrame({
            'close': [100, 102, 105, 103, 108, 110, 112, 115, 113, 118]
        })

        calc = MomentumFactorCalculator(df)
        result = calc.add_momentum_factors(periods=[3])

        # 手动计算第4个值（索引3）
        manual = (df['close'].iloc[3] / df['close'].iloc[0] - 1) * 100
        auto = result['MOM3'].iloc[3]

        assert abs(manual - auto) < 0.0001

    def test_rsi_formula_validation(self):
        """验证RSI公式"""
        # 构造简单数据方便验证
        prices = [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                 111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
        df = pd.DataFrame({'close': prices})

        calc = MomentumFactorCalculator(df)
        result = calc.add_rsi(periods=[14])

        # RSI应该在合理范围内
        valid_rsi = result['RSI14'].dropna()
        assert len(valid_rsi) > 0
        assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()
