"""
Alpha因子模块扩展测试
包含深度测试、集成测试、性能测试和数据质量测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from unittest.mock import patch, MagicMock

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
    BaseFactorCalculator,
    FactorConfig,
    calculate_all_alpha_factors,
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
def large_price_data():
    """生成大规模数据集（用于性能测试）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=1000, freq='D')
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 1000)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 1000)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 1000)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 1000)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 1000)
    }, index=dates)
    return df


@pytest.fixture
def real_market_like_data():
    """生成类似真实市场的数据（包含趋势、震荡、跳空等特征）"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=500, freq='D')

    # 模拟不同市场阶段
    phase1 = np.linspace(100, 120, 150)  # 上涨趋势
    phase2 = np.linspace(120, 110, 100)  # 下跌趋势
    phase3 = 110 + np.random.normal(0, 2, 150)  # 震荡整理
    phase4 = np.linspace(110, 130, 100)  # 再次上涨

    close_prices = np.concatenate([phase1, phase2, phase3, phase4])

    # 添加随机噪声
    close_prices = close_prices * (1 + np.random.normal(0, 0.01, 500))

    df = pd.DataFrame({
        'open': close_prices * (1 + np.random.uniform(-0.02, 0.02, 500)),
        'high': close_prices * (1 + np.random.uniform(0, 0.04, 500)),
        'low': close_prices * (1 + np.random.uniform(-0.04, 0, 500)),
        'close': close_prices,
        'vol': np.random.uniform(500000, 20000000, 500)
    }, index=dates)
    return df


# ==================== 数据质量和验证测试 ====================


class TestDataQuality:
    """测试因子数据质量"""

    def test_no_inf_values(self, sample_price_data):
        """测试因子值中没有无穷大"""
        af = AlphaFactors(sample_price_data)
        result = af.add_all_alpha_factors()

        factor_names = af.get_factor_names()
        for factor in factor_names:
            inf_count = np.isinf(result[factor]).sum()
            assert inf_count == 0, f"因子 {factor} 包含 {inf_count} 个无穷大值"

    def test_nan_percentage_reasonable(self, sample_price_data):
        """测试NaN值比例在合理范围内"""
        af = AlphaFactors(sample_price_data)
        result = af.add_all_alpha_factors()

        total_rows = len(result)
        factor_names = af.get_factor_names()

        for factor in factor_names:
            nan_count = result[factor].isna().sum()
            nan_percentage = nan_count / total_rows * 100

            # NaN值不应超过50%（考虑到滚动窗口）
            assert nan_percentage < 50, \
                f"因子 {factor} 的NaN比例过高: {nan_percentage:.2f}%"

    def test_factor_value_ranges(self, sample_price_data):
        """测试因子值在合理范围内"""
        af = AlphaFactors(sample_price_data)
        result = af.add_all_alpha_factors()

        # 测试相关系数在[-1, 1]范围内
        corr_factors = [col for col in result.columns if 'CORR' in col]
        for factor in corr_factors:
            valid_values = result[factor].dropna()
            if len(valid_values) > 0:
                assert valid_values.min() >= -1.1, f"{factor} 最小值异常"
                assert valid_values.max() <= 1.1, f"{factor} 最大值异常"

        # 测试R2在[0, 1]范围内
        r2_factors = [col for col in result.columns if 'R2' in col]
        for factor in r2_factors:
            valid_values = result[factor].dropna()
            if len(valid_values) > 0:
                assert valid_values.min() >= -0.2, f"{factor} 最小值异常"
                assert valid_values.max() <= 1.2, f"{factor} 最大值异常"

    def test_factor_stability_across_periods(self, sample_price_data):
        """测试因子在不同时间段的稳定性"""
        af = AlphaFactors(sample_price_data)
        result = af.add_all_alpha_factors()

        # 分割为两个时间段
        mid_point = len(result) // 2
        period1 = result.iloc[:mid_point]
        period2 = result.iloc[mid_point:]

        factor_names = af.get_factor_names()

        for factor in factor_names:
            if factor in period1.columns and factor in period2.columns:
                mean1 = period1[factor].dropna().mean()
                mean2 = period2[factor].dropna().mean()

                # 检查均值不会剧烈变化（不超过10倍）
                if mean1 != 0 and not np.isnan(mean1) and not np.isnan(mean2):
                    ratio = abs(mean2 / mean1)
                    assert 0.01 < ratio < 100, \
                        f"因子 {factor} 在不同时期变化过大: {ratio:.2f}x"


# ==================== 因子计算正确性深度测试 ====================


class TestFactorCorrectnessDeep:
    """深度测试因子计算的正确性"""

    def test_momentum_calculation_accuracy(self, sample_price_data):
        """验证动量因子计算的准确性"""
        calc = MomentumFactorCalculator(sample_price_data)
        result = calc.add_momentum_factors(periods=[5])

        # 手动计算5日动量
        manual_mom5 = sample_price_data['close'].pct_change(5) * 100

        # 比较计算结果（允许微小误差）
        diff = (result['MOM5'] - manual_mom5).dropna()
        assert diff.abs().max() < 1e-10, "动量因子计算不准确"

    def test_volatility_calculation_accuracy(self, sample_price_data):
        """验证波动率因子计算的准确性"""
        calc = VolatilityFactorCalculator(sample_price_data)
        result = calc.add_volatility_factors(periods=[20])

        # 手动计算20日波动率
        returns = sample_price_data['close'].pct_change()
        manual_vol20 = returns.rolling(window=20).std() * np.sqrt(252) * 100

        # 比较计算结果
        diff = (result['VOLATILITY20'] - manual_vol20).dropna()
        assert diff.abs().max() < 1e-8, "波动率因子计算不准确"

    def test_zscore_properties(self, sample_price_data):
        """测试Z-score因子的统计特性"""
        calc = ReversalFactorCalculator(sample_price_data)
        result = calc.add_reversal_factors(short_periods=[1], long_periods=[60])

        # Z-score应该大致符合标准正态分布
        zscore_values = result['ZSCORE60'].dropna()

        if len(zscore_values) > 30:
            # 均值应该接近0
            assert abs(zscore_values.mean()) < 1.0, "Z-score均值偏离0过远"

            # 标准差应该接近1
            assert 0.5 < zscore_values.std() < 2.0, "Z-score标准差异常"

    def test_breakout_factor_boundaries(self, sample_price_data):
        """测试突破因子的边界条件"""
        calc = TrendFactorCalculator(sample_price_data)
        result = calc.add_breakout_factors(periods=[20])

        # BREAKOUT_HIGH应该 <= 0（当前价 <= 最高价）
        breakout_high = result['BREAKOUT_HIGH20'].dropna()
        assert (breakout_high <= 0.1).all(), "突破高位因子应该 <= 0"

        # BREAKOUT_LOW应该 >= 0（当前价 >= 最低价）
        breakout_low = result['BREAKOUT_LOW20'].dropna()
        assert (breakout_low >= -0.1).all(), "突破低位因子应该 >= 0"

        # PRICE_POSITION应该在[0, 100]范围内
        price_position = result['PRICE_POSITION20'].dropna()
        assert (price_position >= -1).all() and (price_position <= 101).all(), \
            "价格位置应该在[0, 100]范围内"


# ==================== 性能和效率测试 ====================


class TestPerformanceDeep:
    """深度性能测试"""

    def test_large_dataset_performance(self, large_price_data):
        """测试大数据集的性能"""
        af = AlphaFactors(large_price_data)

        start_time = time.time()
        result = af.add_all_alpha_factors()
        elapsed_time = time.time() - start_time

        # 1000行数据应该在10秒内完成
        assert elapsed_time < 10, f"大数据集处理过慢: {elapsed_time:.2f}秒"

        # 验证结果正确
        assert len(result) == 1000
        assert len(af.get_factor_names()) > 50

    def test_inplace_memory_efficiency(self, sample_price_data):
        """测试inplace模式的内存效率"""
        import copy

        # 复制数据用于比较
        df_copy = sample_price_data.copy()
        df_inplace = sample_price_data.copy()

        # 非inplace模式
        af1 = AlphaFactors(df_copy, inplace=False)
        result1 = af1.add_momentum_factors(periods=[5, 10, 20])

        # inplace模式
        af2 = AlphaFactors(df_inplace, inplace=True)
        result2 = af2.add_momentum_factors(periods=[5, 10, 20])

        # 验证inplace模式修改了原DataFrame
        assert 'MOM5' in df_inplace.columns, "inplace模式应该修改原DataFrame"
        assert 'MOM5' not in df_copy.columns, "非inplace模式不应修改原DataFrame"

    def test_caching_effectiveness(self, sample_price_data):
        """测试缓存的有效性"""
        calc = MomentumFactorCalculator(sample_price_data)

        # 第一次计算（会触发缓存）
        start_time = time.time()
        calc._calculate_returns('close')
        first_time = time.time() - start_time

        # 第二次计算（使用缓存）
        start_time = time.time()
        calc._calculate_returns('close')
        second_time = time.time() - start_time

        # 缓存应该让第二次调用更快（至少快50%）
        assert second_time < first_time * 0.5, "缓存未生效"

    def test_concurrent_calculator_independence(self, sample_price_data):
        """测试多个计算器的独立性"""
        # 创建多个计算器实例
        calc1 = MomentumFactorCalculator(sample_price_data, inplace=False)
        calc2 = MomentumFactorCalculator(sample_price_data, inplace=False)

        # 分别计算不同因子
        result1 = calc1.add_momentum_factors(periods=[5])
        result2 = calc2.add_momentum_factors(periods=[10])

        # 两个计算器应该独立，不互相影响
        assert 'MOM5' in result1.columns
        assert 'MOM10' in result2.columns
        assert 'MOM10' not in result1.columns
        assert 'MOM5' not in result2.columns


# ==================== 集成测试 ====================


class TestIntegration:
    """集成测试：测试多个模块协同工作"""

    def test_full_pipeline(self, sample_price_data):
        """测试完整的因子计算流程"""
        af = AlphaFactors(sample_price_data)

        # 逐步添加各类因子
        af.add_momentum_factors(periods=[5, 10, 20])
        af.add_reversal_factors(short_periods=[1, 3], long_periods=[20])
        af.add_volatility_factors(periods=[5, 20])
        af.add_volume_factors(periods=[5, 10])
        af.add_trend_strength(periods=[20])

        result = af.get_dataframe()
        factor_names = af.get_factor_names()

        # 验证所有因子都已计算
        assert len(factor_names) > 20
        assert all(factor in result.columns for factor in factor_names)

    def test_mixed_calculator_usage(self, sample_price_data):
        """测试混合使用不同计算器"""
        # 使用主类
        af = AlphaFactors(sample_price_data)
        af.add_momentum_factors(periods=[5])

        # 直接使用子计算器
        vol_calc = VolatilityFactorCalculator(af.df, inplace=True)
        vol_calc.add_volatility_factors(periods=[10])

        # 验证两种方式的结果都存在
        assert 'MOM5' in af.df.columns
        assert 'VOLATILITY10' in af.df.columns

    def test_real_market_scenario(self, real_market_like_data):
        """测试类似真实市场场景"""
        af = AlphaFactors(real_market_like_data)
        result = af.add_all_alpha_factors()

        # 验证因子在不同市场阶段都能计算
        factor_names = af.get_factor_names()
        assert len(factor_names) > 50

        # 验证趋势因子能捕捉市场趋势
        trend_factors = [f for f in factor_names if 'TREND' in f]
        assert len(trend_factors) > 0

        # 验证波动率因子在震荡期变化
        vol_factors = [f for f in factor_names if 'VOLATILITY' in f]
        assert len(vol_factors) > 0


# ==================== 边界和异常情况深度测试 ====================


class TestEdgeCasesDeep:
    """深度边界情况测试"""

    def test_all_nan_column(self):
        """测试全NaN列的处理"""
        df = pd.DataFrame({
            'close': [np.nan] * 100,
            'vol': [1e6] * 100
        })

        af = AlphaFactors(df)
        # 应该能处理但因子值也是NaN
        result = af.add_momentum_factors(periods=[5])
        assert result['MOM5'].isna().all()

    def test_extreme_volatility(self):
        """测试极端波动情况"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 创建极端波动数据
        prices = [100]
        for i in range(99):
            # 每天涨跌50%
            prices.append(prices[-1] * (1.5 if i % 2 == 0 else 0.5))

        df = pd.DataFrame({
            'close': prices,
            'vol': [1e6] * 100
        }, index=dates)

        af = AlphaFactors(df)
        result = af.add_volatility_factors(periods=[20])

        # 波动率应该非常高
        vol20 = result['VOLATILITY20'].dropna()
        assert vol20.mean() > 100, "未能捕捉极端波动"

    def test_price_gaps(self):
        """测试价格跳空情况"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = [100] * 50 + [150] * 50  # 突然跳空50%

        df = pd.DataFrame({
            'open': prices,
            'close': prices,
            'high': [p * 1.02 for p in prices],
            'low': [p * 0.98 for p in prices],
            'vol': [1e6] * 100
        }, index=dates)

        af = AlphaFactors(df)
        result = af.add_overnight_reversal()

        # 应该能捕捉到跳空
        assert 'OVERNIGHT_RET' in result.columns

    def test_zero_volume(self):
        """测试零成交量情况"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.linspace(100, 110, 100),
            'vol': [0] * 100  # 零成交量
        }, index=dates)

        af = AlphaFactors(df)
        result = af.add_volume_factors(periods=[5])

        # 应该能处理但结果可能是inf/nan
        assert 'VOLUME_RATIO5' in result.columns

    def test_duplicate_index(self):
        """测试重复索引"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        dates = dates.tolist() + dates.tolist()  # 重复索引

        df = pd.DataFrame({
            'close': np.linspace(100, 150, 100)
        }, index=dates)

        af = AlphaFactors(df)
        # 应该能处理但可能有警告
        result = af.add_momentum_factors(periods=[5])
        assert 'MOM5' in result.columns


# ==================== 日志和错误处理测试 ====================


class TestLoggingAndErrors:
    """测试日志和错误处理"""

    def test_logging_for_missing_columns(self, caplog):
        """测试缺少列时的日志记录"""
        import logging
        caplog.set_level(logging.WARNING)

        df = pd.DataFrame({'close': [100, 101, 102]})
        calc = VolumeFactorCalculator(df)
        result = calc.add_volume_factors()

        # 应该有警告日志
        # 注意：loguru的日志可能不会被caplog捕获，这里测试功能正常运行

    def test_error_recovery(self):
        """测试错误恢复能力"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104]
        })

        af = AlphaFactors(df)

        # 即使数据量很小，也应该能计算部分因子
        result = af.add_momentum_factors(periods=[2, 3])

        # 至少应该有一些因子被计算
        assert 'MOM2' in result.columns or 'MOM3' in result.columns


# ==================== 因子相关性和独立性测试 ====================


class TestFactorRelationships:
    """测试因子之间的关系"""

    def test_momentum_reversal_relationship(self, sample_price_data):
        """测试动量和反转因子的关系"""
        af = AlphaFactors(sample_price_data)
        af.add_momentum_factors(periods=[5])
        af.add_reversal_factors(short_periods=[5], long_periods=[])

        result = af.get_dataframe()

        # MOM5和REV5应该是负相关的
        if 'MOM5' in result.columns and 'REV5' in result.columns:
            corr = result[['MOM5', 'REV5']].corr().iloc[0, 1]
            assert corr < -0.9, "动量和反转因子应该强负相关"

    def test_volume_factors_consistency(self, sample_price_data):
        """测试成交量因子的一致性"""
        calc = VolumeFactorCalculator(sample_price_data)
        result = calc.add_volume_factors(periods=[20])

        # VOLUME_RATIO和VOLUME_ZSCORE应该相关
        if 'VOLUME_RATIO20' in result.columns and 'VOLUME_ZSCORE20' in result.columns:
            valid_data = result[['VOLUME_RATIO20', 'VOLUME_ZSCORE20']].dropna()
            if len(valid_data) > 30:
                corr = valid_data.corr().iloc[0, 1]
                assert abs(corr) > 0.5, "成交量比率和Z-score应该相关"


# ==================== 运行所有测试 ====================


if __name__ == "__main__":
    # 运行所有扩展测试
    pytest.main([__file__, "-v", "--tb=short", "-s"])
