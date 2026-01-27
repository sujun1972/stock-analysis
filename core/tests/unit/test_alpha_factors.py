"""
Alpha因子模块单元测试
测试所有因子计算器的功能和边界情况
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 导入要测试的模块
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from features.alpha_factors import (
    AlphaFactors,
    MomentumFactorCalculator,
    ReversalFactorCalculator,
    VolatilityFactorCalculator,
    VolumeFactorCalculator,
    TrendFactorCalculator,
    LiquidityFactorCalculator,
    FactorConfig,
    calculate_all_alpha_factors,
    calculate_momentum_factors,
    calculate_reversal_factors
)


# ==================== 测试数据生成 ====================


@pytest.fixture
def sample_price_data():
    """生成样本价格数据"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 300)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 300)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 300)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 300)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)

    return df


@pytest.fixture
def minimal_price_data():
    """生成最小必需的价格数据（仅close列）"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = np.linspace(100, 110, 100)  # 简单的线性增长

    df = pd.DataFrame({
        'close': prices
    }, index=dates)

    return df


@pytest.fixture
def small_price_data():
    """生成小数据集（测试边界情况）"""
    dates = pd.date_range('2023-01-01', periods=10, freq='D')

    df = pd.DataFrame({
        'open': [100, 101, 102, 101, 103, 104, 103, 105, 106, 107],
        'high': [102, 103, 104, 103, 105, 106, 105, 107, 108, 109],
        'low': [99, 100, 101, 100, 102, 103, 102, 104, 105, 106],
        'close': [101, 102, 103, 102, 104, 105, 104, 106, 107, 108],
        'vol': [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6, 1.5e6, 1.6e6, 1.7e6, 1.8e6, 1.9e6]
    }, index=dates)

    return df


# ==================== 配置类测试 ====================


class TestFactorConfig:
    """测试因子配置类"""

    def test_default_periods(self):
        """测试默认周期配置"""
        assert FactorConfig.DEFAULT_SHORT_PERIODS == [5, 10, 20]
        assert FactorConfig.DEFAULT_MEDIUM_PERIODS == [20, 60]
        assert FactorConfig.DEFAULT_LONG_PERIODS == [60, 120]

    def test_column_names(self):
        """测试列名配置"""
        assert 'close' in FactorConfig.PRICE_COLUMNS
        assert 'vol' in FactorConfig.VOLUME_COLUMNS
        assert 'volume' in FactorConfig.VOLUME_COLUMNS

    def test_constants(self):
        """测试常量配置"""
        assert FactorConfig.ANNUAL_TRADING_DAYS == 252
        assert FactorConfig.EPSILON == 1e-8


# ==================== 动量因子测试 ====================


class TestMomentumFactorCalculator:
    """测试动量因子计算器"""

    def test_initialization(self, sample_price_data):
        """测试初始化"""
        calc = MomentumFactorCalculator(sample_price_data)
        assert calc.df is not None
        assert len(calc.df) == len(sample_price_data)

    def test_validation_missing_close(self):
        """测试缺少close列时的验证"""
        df = pd.DataFrame({'open': [100, 101, 102]})
        with pytest.raises(ValueError, match="缺少必需的列: close"):
            MomentumFactorCalculator(df)

    def test_add_momentum_factors(self, sample_price_data):
        """测试添加动量因子"""
        calc = MomentumFactorCalculator(sample_price_data)
        result = calc.add_momentum_factors(periods=[5, 10, 20])

        # 检查因子列是否创建
        assert 'MOM5' in result.columns
        assert 'MOM10' in result.columns
        assert 'MOM20' in result.columns
        assert 'MOM_LOG5' in result.columns
        assert 'MOM_LOG10' in result.columns
        assert 'MOM_LOG20' in result.columns

        # 检查数值合理性
        assert not result['MOM5'].isna().all()
        assert result['MOM5'].iloc[:5].isna().all()  # 前5个应该是NaN

    def test_add_relative_strength(self, sample_price_data):
        """测试添加相对强度因子"""
        calc = MomentumFactorCalculator(sample_price_data)
        result = calc.add_relative_strength(periods=[20, 60])

        assert 'RS20' in result.columns
        assert 'RS60' in result.columns

        # 检查数值范围（相对强度应该在合理范围内）
        rs20_valid = result['RS20'].dropna()
        assert len(rs20_valid) > 0

    def test_add_acceleration(self, sample_price_data):
        """测试添加加速度因子"""
        calc = MomentumFactorCalculator(sample_price_data)
        result = calc.add_acceleration(periods=[5, 10])

        assert 'ACC5' in result.columns
        assert 'ACC10' in result.columns

    def test_calculate_all(self, sample_price_data):
        """测试计算所有动量因子"""
        calc = MomentumFactorCalculator(sample_price_data)
        result = calc.calculate_all()

        # 检查所有类型的因子都已创建
        assert any('MOM' in col for col in result.columns)
        assert any('RS' in col for col in result.columns)
        assert any('ACC' in col for col in result.columns)

    def test_inplace_modification(self, sample_price_data):
        """测试原地修改模式"""
        calc = MomentumFactorCalculator(sample_price_data, inplace=True)
        calc.add_momentum_factors(periods=[5])

        # inplace=True时，原DataFrame应该被修改
        assert 'MOM5' in calc.df.columns


# ==================== 反转因子测试 ====================


class TestReversalFactorCalculator:
    """测试反转因子计算器"""

    def test_add_reversal_factors(self, sample_price_data):
        """测试添加反转因子"""
        calc = ReversalFactorCalculator(sample_price_data)
        result = calc.add_reversal_factors(short_periods=[1, 3, 5], long_periods=[20, 60])

        # 短期反转因子
        assert 'REV1' in result.columns
        assert 'REV3' in result.columns
        assert 'REV5' in result.columns

        # 长期反转因子（Z-score）
        assert 'ZSCORE20' in result.columns
        assert 'ZSCORE60' in result.columns

    def test_add_overnight_reversal(self, sample_price_data):
        """测试添加隔夜反转因子"""
        calc = ReversalFactorCalculator(sample_price_data)
        result = calc.add_overnight_reversal()

        assert 'OVERNIGHT_RET' in result.columns
        assert 'INTRADAY_RET' in result.columns
        assert 'OVERNIGHT_REV' in result.columns

    def test_overnight_reversal_missing_open(self, minimal_price_data):
        """测试缺少open列时的隔夜反转"""
        calc = ReversalFactorCalculator(minimal_price_data)
        result = calc.add_overnight_reversal()

        # 应该跳过但不报错
        assert 'OVERNIGHT_RET' not in result.columns

    def test_calculate_all(self, sample_price_data):
        """测试计算所有反转因子"""
        calc = ReversalFactorCalculator(sample_price_data)
        result = calc.calculate_all()

        assert any('REV' in col for col in result.columns)
        assert any('ZSCORE' in col for col in result.columns)


# ==================== 波动率因子测试 ====================


class TestVolatilityFactorCalculator:
    """测试波动率因子计算器"""

    def test_add_volatility_factors(self, sample_price_data):
        """测试添加波动率因子"""
        calc = VolatilityFactorCalculator(sample_price_data)
        result = calc.add_volatility_factors(periods=[5, 10, 20])

        assert 'VOLATILITY5' in result.columns
        assert 'VOLATILITY10' in result.columns
        assert 'VOLATILITY20' in result.columns
        assert 'VOLSKEW5' in result.columns

        # 检查波动率为正
        vol_valid = result['VOLATILITY20'].dropna()
        assert (vol_valid >= 0).all()

    def test_add_high_low_volatility(self, sample_price_data):
        """测试添加Parkinson波动率因子"""
        calc = VolatilityFactorCalculator(sample_price_data)
        result = calc.add_high_low_volatility(periods=[10, 20])

        assert 'PARKINSON_VOL10' in result.columns
        assert 'PARKINSON_VOL20' in result.columns

    def test_high_low_volatility_missing_columns(self, minimal_price_data):
        """测试缺少high/low列时的Parkinson波动率"""
        calc = VolatilityFactorCalculator(minimal_price_data)
        result = calc.add_high_low_volatility()

        # 应该跳过但不报错
        assert 'PARKINSON_VOL10' not in result.columns

    def test_calculate_all(self, sample_price_data):
        """测试计算所有波动率因子"""
        calc = VolatilityFactorCalculator(sample_price_data)
        result = calc.calculate_all()

        assert any('VOLATILITY' in col for col in result.columns)


# ==================== 成交量因子测试 ====================


class TestVolumeFactorCalculator:
    """测试成交量因子计算器"""

    def test_add_volume_factors(self, sample_price_data):
        """测试添加成交量因子"""
        calc = VolumeFactorCalculator(sample_price_data)
        result = calc.add_volume_factors(periods=[5, 10, 20])

        assert 'VOLUME_CHG5' in result.columns
        assert 'VOLUME_RATIO5' in result.columns
        assert 'VOLUME_ZSCORE5' in result.columns

    def test_add_price_volume_correlation(self, sample_price_data):
        """测试添加价量相关性因子"""
        calc = VolumeFactorCalculator(sample_price_data)
        result = calc.add_price_volume_correlation(periods=[20, 60])

        assert 'PV_CORR20' in result.columns
        assert 'PV_CORR60' in result.columns

        # 相关系数应该在[-1, 1]范围内
        corr_valid = result['PV_CORR20'].dropna()
        if len(corr_valid) > 0:
            assert (corr_valid >= -1).all() and (corr_valid <= 1).all()

    def test_volume_factors_missing_volume(self, minimal_price_data):
        """测试缺少成交量列时的处理"""
        calc = VolumeFactorCalculator(minimal_price_data)
        result = calc.add_volume_factors()

        # 应该跳过但不报错
        assert 'VOLUME_CHG5' not in result.columns

    def test_calculate_all(self, sample_price_data):
        """测试计算所有成交量因子"""
        calc = VolumeFactorCalculator(sample_price_data)
        result = calc.calculate_all()

        assert any('VOLUME' in col for col in result.columns)


# ==================== 趋势因子测试 ====================


class TestTrendFactorCalculator:
    """测试趋势因子计算器"""

    def test_add_trend_strength(self, sample_price_data):
        """测试添加趋势强度因子"""
        calc = TrendFactorCalculator(sample_price_data)
        result = calc.add_trend_strength(periods=[20, 60])

        assert 'TREND20' in result.columns
        assert 'TREND60' in result.columns
        assert 'TREND_R2_20' in result.columns
        assert 'TREND_R2_60' in result.columns

        # R2应该在[0, 1]范围内
        r2_valid = result['TREND_R2_20'].dropna()
        if len(r2_valid) > 0:
            assert (r2_valid >= -0.1).all() and (r2_valid <= 1.1).all()  # 允许轻微误差

    def test_add_breakout_factors(self, sample_price_data):
        """测试添加突破因子"""
        calc = TrendFactorCalculator(sample_price_data)
        result = calc.add_breakout_factors(periods=[20, 60])

        assert 'BREAKOUT_HIGH20' in result.columns
        assert 'BREAKOUT_LOW20' in result.columns
        assert 'PRICE_POSITION20' in result.columns

        # 价格位置应该在[0, 100]范围内
        pos_valid = result['PRICE_POSITION20'].dropna()
        if len(pos_valid) > 0:
            assert (pos_valid >= -1).all() and (pos_valid <= 101).all()  # 允许轻微误差

    def test_calculate_all(self, sample_price_data):
        """测试计算所有趋势因子"""
        calc = TrendFactorCalculator(sample_price_data)
        result = calc.calculate_all()

        assert any('TREND' in col for col in result.columns)
        assert any('BREAKOUT' in col for col in result.columns)


# ==================== 流动性因子测试 ====================


class TestLiquidityFactorCalculator:
    """测试流动性因子计算器"""

    def test_add_liquidity_factors(self, sample_price_data):
        """测试添加流动性因子"""
        calc = LiquidityFactorCalculator(sample_price_data)
        result = calc.add_liquidity_factors(periods=[20])

        assert 'ILLIQUIDITY20' in result.columns

        # 非流动性指标应该为正
        illiq_valid = result['ILLIQUIDITY20'].dropna()
        if len(illiq_valid) > 0:
            assert (illiq_valid >= 0).all()

    def test_liquidity_factors_missing_volume(self, minimal_price_data):
        """测试缺少成交量列时的处理"""
        calc = LiquidityFactorCalculator(minimal_price_data)
        result = calc.add_liquidity_factors()

        # 应该跳过但不报错
        assert 'ILLIQUIDITY20' not in result.columns


# ==================== 主Alpha因子类测试 ====================


class TestAlphaFactors:
    """测试主Alpha因子类"""

    def test_initialization(self, sample_price_data):
        """测试初始化"""
        af = AlphaFactors(sample_price_data)
        assert af.df is not None
        assert af.momentum is not None
        assert af.reversal is not None
        assert af.volatility is not None
        assert af.volume is not None
        assert af.trend is not None
        assert af.liquidity is not None

    def test_validation_missing_close(self):
        """测试缺少close列时的验证"""
        df = pd.DataFrame({'open': [100, 101, 102]})
        with pytest.raises(ValueError, match="缺少必需的列"):
            AlphaFactors(df)

    def test_add_all_alpha_factors(self, sample_price_data):
        """测试一键添加所有因子"""
        af = AlphaFactors(sample_price_data)
        result = af.add_all_alpha_factors()

        # 检查各类因子都已添加
        factor_names = af.get_factor_names()
        assert len(factor_names) > 50  # 应该有大量因子

        # 检查各类因子都存在
        assert any('MOM' in f for f in factor_names)
        assert any('REV' in f for f in factor_names)
        assert any('VOLATILITY' in f for f in factor_names)
        assert any('VOLUME' in f for f in factor_names)
        assert any('TREND' in f for f in factor_names)

    def test_get_factor_names(self, sample_price_data):
        """测试获取因子名称"""
        af = AlphaFactors(sample_price_data)
        af.add_momentum_factors(periods=[5, 10])

        factor_names = af.get_factor_names()

        # 应该包含新添加的因子
        assert 'MOM5' in factor_names
        assert 'MOM10' in factor_names

        # 不应包含原始列
        assert 'close' not in factor_names
        assert 'open' not in factor_names

    def test_get_factor_summary(self, sample_price_data):
        """测试获取因子统计摘要"""
        af = AlphaFactors(sample_price_data)
        af.add_all_alpha_factors()

        summary = af.get_factor_summary()

        assert '动量类' in summary
        assert '反转类' in summary
        assert '波动率类' in summary
        assert '成交量类' in summary
        assert '趋势类' in summary
        assert '流动性类' in summary

        # 各类因子数量应该大于0
        assert summary['动量类'] > 0
        assert summary['反转类'] > 0

    def test_inplace_false(self, sample_price_data):
        """测试inplace=False时不修改原DataFrame"""
        original_cols = list(sample_price_data.columns)

        af = AlphaFactors(sample_price_data, inplace=False)
        af.add_momentum_factors(periods=[5])

        # 原DataFrame不应该被修改
        assert list(sample_price_data.columns) == original_cols

    def test_inplace_true(self, sample_price_data):
        """测试inplace=True时修改原DataFrame"""
        af = AlphaFactors(sample_price_data, inplace=True)
        af.add_momentum_factors(periods=[5])

        # 原DataFrame应该被修改
        assert 'MOM5' in sample_price_data.columns

    def test_individual_factor_methods(self, sample_price_data):
        """测试单独调用各类因子方法"""
        af = AlphaFactors(sample_price_data)

        # 测试各个便捷方法
        af.add_momentum_factors(periods=[5])
        assert 'MOM5' in af.df.columns

        af.add_reversal_factors(short_periods=[1], long_periods=[20])
        assert 'REV1' in af.df.columns

        af.add_volatility_factors(periods=[5])
        assert 'VOLATILITY5' in af.df.columns


# ==================== 便捷函数测试 ====================


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_calculate_all_alpha_factors(self, sample_price_data):
        """测试一键计算所有因子的便捷函数"""
        result = calculate_all_alpha_factors(sample_price_data, inplace=False)

        # 检查返回的是新DataFrame
        assert result is not sample_price_data
        assert len(result.columns) > len(sample_price_data.columns)

    def test_calculate_momentum_factors(self, sample_price_data):
        """测试计算动量因子的便捷函数"""
        result = calculate_momentum_factors(sample_price_data, inplace=False)

        # 应该包含动量因子
        assert any('MOM' in col for col in result.columns)
        assert any('RS' in col for col in result.columns)
        assert any('ACC' in col for col in result.columns)

    def test_calculate_reversal_factors(self, sample_price_data):
        """测试计算反转因子的便捷函数"""
        result = calculate_reversal_factors(sample_price_data, inplace=False)

        # 应该包含反转因子
        assert any('REV' in col for col in result.columns)
        assert any('ZSCORE' in col for col in result.columns)


# ==================== 边界情况和异常测试 ====================


class TestEdgeCases:
    """测试边界情况"""

    def test_small_dataset(self, small_price_data):
        """测试小数据集"""
        af = AlphaFactors(small_price_data)

        # 使用较小的周期避免数据不足
        af.add_momentum_factors(periods=[3, 5])
        af.add_volatility_factors(periods=[3, 5])

        # 应该能正常计算
        assert 'MOM3' in af.df.columns
        assert 'VOLATILITY3' in af.df.columns

    def test_single_row(self):
        """测试单行数据"""
        df = pd.DataFrame({'close': [100]})
        af = AlphaFactors(df)

        # 不应该报错，但因子值应该是NaN
        result = af.add_momentum_factors(periods=[1])
        assert 'MOM1' in result.columns
        assert pd.isna(result['MOM1'].iloc[0])

    def test_constant_prices(self):
        """测试价格恒定的情况"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': [100] * 100,
            'vol': [1e6] * 100
        }, index=dates)

        af = AlphaFactors(df)
        result = af.add_all_alpha_factors()

        # 动量应该接近0
        mom_cols = [col for col in result.columns if col.startswith('MOM')]
        for col in mom_cols:
            valid_values = result[col].dropna()
            if len(valid_values) > 0:
                assert (valid_values.abs() < 0.01).all()

    def test_missing_values(self):
        """测试包含缺失值的数据"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = np.linspace(100, 110, 100)
        prices[50:55] = np.nan  # 插入缺失值

        df = pd.DataFrame({
            'close': prices,
            'vol': [1e6] * 100
        }, index=dates)

        af = AlphaFactors(df)

        # 应该能处理缺失值而不报错
        result = af.add_momentum_factors(periods=[5, 10])
        assert 'MOM5' in result.columns


# ==================== 性能测试 ====================


class TestPerformance:
    """测试性能相关功能"""

    def test_caching(self, sample_price_data):
        """测试收益率缓存功能"""
        calc = MomentumFactorCalculator(sample_price_data)

        # 第一次调用会计算并缓存
        returns1 = calc._calculate_returns('close')

        # 第二次调用应该使用缓存
        returns2 = calc._calculate_returns('close')

        # 应该返回相同的对象
        assert returns1 is returns2

    def test_safe_divide(self, sample_price_data):
        """测试安全除法不会产生除零错误"""
        calc = MomentumFactorCalculator(sample_price_data)

        numerator = pd.Series([1, 2, 3])
        denominator = pd.Series([0, 0, 0])

        result = calc._safe_divide(numerator, denominator)

        # 应该不产生inf
        assert not np.isinf(result).any()


# ==================== 运行测试 ====================


if __name__ == "__main__":
    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
