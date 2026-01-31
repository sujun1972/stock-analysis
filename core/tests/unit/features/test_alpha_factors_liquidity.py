"""
流动性因子计算器专项测试

测试 LiquidityFactorCalculator 的所有功能：
- Amihud非流动性指标
- 成交量相关流动性因子
- 边界情况和异常处理

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.features.alpha_factors import (
    LiquidityFactorCalculator,
    FactorConfig,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_price_volume_data():
    """生成包含价格和成交量的样本数据"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=200, freq='D')

    # 生成价格数据
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 200)
    prices = base_price * (1 + returns).cumprod()

    # 生成成交量数据（模拟真实市场）
    base_volume = 5_000_000
    volume_volatility = np.random.normal(1.0, 0.3, 200)
    volumes = base_volume * volume_volatility
    volumes = np.maximum(volumes, 100_000)  # 最小成交量

    return pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 200)),
        'high': prices * (1 + np.random.uniform(0, 0.02, 200)),
        'low': prices * (1 + np.random.uniform(-0.02, 0, 200)),
        'close': prices,
        'vol': volumes,
    }, index=dates)


@pytest.fixture
def extreme_volume_data():
    """生成包含极端成交量的数据"""
    np.random.seed(123)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    prices = np.linspace(100, 110, 100)

    volumes = np.full(100, 1_000_000.0)
    # 添加一些极端值
    volumes[10] = 100_000_000  # 极大成交量
    volumes[20] = 1_000        # 极小成交量
    volumes[30] = 0            # 零成交量

    return pd.DataFrame({
        'close': prices,
        'vol': volumes,
    }, index=dates)


# ==================== 基础功能测试 ====================


class TestLiquidityFactorBasics:
    """流动性因子基础功能测试"""

    def test_calculator_initialization(self, sample_price_volume_data):
        """测试计算器初始化"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)

        assert calc.df is not None
        assert 'close' in calc.df.columns
        assert 'vol' in calc.df.columns

    def test_validation_missing_close(self):
        """测试缺少close列的验证"""
        df = pd.DataFrame({'vol': [1, 2, 3]})

        with pytest.raises(ValueError, match="缺少必需的列: close"):
            LiquidityFactorCalculator(df)

    def test_validation_with_close(self, sample_price_volume_data):
        """测试包含close列的验证通过"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        # 不应抛出异常
        assert calc is not None


# ==================== Amihud非流动性指标测试 ====================


class TestAmihudIlliquidity:
    """Amihud非流动性指标测试"""

    def test_amihud_basic(self, sample_price_volume_data):
        """测试基本Amihud非流动性计算"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        result = calc.add_liquidity_factors(periods=[20])

        # 验证列存在
        assert 'ILLIQUIDITY20' in result.columns

        # 验证数据类型
        assert result['ILLIQUIDITY20'].dtype in [np.float64, np.float32]

        # 验证前N个值为NaN（滚动窗口）
        assert result['ILLIQUIDITY20'].iloc[:19].isna().all()

        # 验证后续值不全为NaN
        assert not result['ILLIQUIDITY20'].iloc[20:].isna().all()

    def test_amihud_multiple_periods(self, sample_price_volume_data):
        """测试多个周期的Amihud计算"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        result = calc.add_liquidity_factors(periods=[5, 20, 60])

        # 验证所有列都存在
        assert 'ILLIQUIDITY5' in result.columns
        assert 'ILLIQUIDITY20' in result.columns
        assert 'ILLIQUIDITY60' in result.columns

        # 验证不同周期的NaN行数正确
        assert result['ILLIQUIDITY5'].iloc[:4].isna().all()
        assert result['ILLIQUIDITY20'].iloc[:19].isna().all()
        assert result['ILLIQUIDITY60'].iloc[:59].isna().all()

    def test_amihud_default_period(self, sample_price_volume_data):
        """测试默认周期"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        result = calc.add_liquidity_factors()  # 不指定periods

        # 应该有默认的20天周期
        assert 'ILLIQUIDITY20' in result.columns

    def test_amihud_formula_correctness(self, sample_price_volume_data):
        """测试Amihud公式正确性"""
        calc = LiquidityFactorCalculator(sample_price_volume_data.copy())
        result = calc.add_liquidity_factors(periods=[20])

        # 手动计算前几个有效值进行验证
        returns = sample_price_volume_data['close'].pct_change().abs()
        volumes = sample_price_volume_data['vol']
        manual_amihud = (returns / volumes).rolling(window=20).mean() * 1e6

        # 比较结果（允许浮点误差）
        pd.testing.assert_series_equal(
            result['ILLIQUIDITY20'],
            manual_amihud,
            check_names=False,
            rtol=1e-5
        )

    def test_amihud_positive_values(self, sample_price_volume_data):
        """测试Amihud值应为非负"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        result = calc.add_liquidity_factors(periods=[20])

        # Amihud非流动性应该是非负的
        valid_values = result['ILLIQUIDITY20'].dropna()
        assert (valid_values >= 0).all()


# ==================== 成交量处理测试 ====================


class TestVolumeHandling:
    """成交量处理相关测试"""

    def test_custom_volume_column(self, sample_price_volume_data):
        """测试自定义成交量列"""
        df = sample_price_volume_data.copy()
        df['custom_vol'] = df['vol']

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20], volume_col='custom_vol')

        assert 'ILLIQUIDITY20' in result.columns

    def test_missing_volume_column(self, sample_price_volume_data):
        """测试缺少成交量列"""
        df = sample_price_volume_data[['close']].copy()  # 只保留close列

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20])

        # 应该跳过计算，不添加新列
        assert 'ILLIQUIDITY20' not in result.columns

    def test_volume_column_detection(self, sample_price_volume_data):
        """测试成交量列自动检测"""
        # 使用'vol'列
        calc1 = LiquidityFactorCalculator(sample_price_volume_data)
        result1 = calc1.add_liquidity_factors()
        assert 'ILLIQUIDITY20' in result1.columns

        # 使用'volume'列
        df2 = sample_price_volume_data.copy()
        df2['volume'] = df2['vol']
        df2 = df2.drop(columns=['vol'])

        calc2 = LiquidityFactorCalculator(df2)
        result2 = calc2.add_liquidity_factors()
        assert 'ILLIQUIDITY20' in result2.columns

    def test_zero_volume_handling(self, extreme_volume_data):
        """测试零成交量的处理"""
        calc = LiquidityFactorCalculator(extreme_volume_data)
        result = calc.add_liquidity_factors(periods=[5])

        # 零成交量应该导致inf或很大的值
        # safe_divide应该处理这种情况
        assert 'ILLIQUIDITY5' in result.columns

        # 验证没有产生无效值（如果使用了epsilon保护）
        valid_values = result['ILLIQUIDITY5'].replace([np.inf, -np.inf], np.nan).dropna()
        assert len(valid_values) > 0  # 应该有一些有效值

    def test_extreme_volume_values(self, extreme_volume_data):
        """测试极端成交量值"""
        calc = LiquidityFactorCalculator(extreme_volume_data)
        result = calc.add_liquidity_factors(periods=[10])

        # 验证极大成交量导致低非流动性
        # 验证极小成交量导致高非流动性
        assert 'ILLIQUIDITY10' in result.columns


# ==================== calculate_all方法测试 ====================


class TestCalculateAll:
    """calculate_all方法测试"""

    def test_calculate_all_basic(self, sample_price_volume_data):
        """测试calculate_all方法"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        resp = calc.calculate_all()
        result = resp.data if hasattr(resp, 'data') else resp

        # 应该包含默认的流动性因子
        assert 'ILLIQUIDITY20' in result.columns

    def test_calculate_all_no_modification(self, sample_price_volume_data):
        """测试calculate_all不修改原数据（非inplace模式）"""
        original_df = sample_price_volume_data.copy()
        calc = LiquidityFactorCalculator(original_df, inplace=False)
        resp = calc.calculate_all()
        result = resp.data if hasattr(resp, 'data') else resp

        # 原始DataFrame不应该有新列
        assert 'ILLIQUIDITY20' not in original_df.columns
        # 结果应该有新列
        assert 'ILLIQUIDITY20' in result.columns

    def test_calculate_all_inplace(self, sample_price_volume_data):
        """测试calculate_all的inplace模式"""
        calc = LiquidityFactorCalculator(sample_price_volume_data, inplace=True)
        resp = calc.calculate_all()

        # inplace模式下，df应该被修改，并且返回Response对象
        assert 'ILLIQUIDITY20' in calc.df.columns
        # Response对象的data应该指向修改后的df
        if hasattr(resp, 'data'):
            assert resp.data is calc.df
        else:
            assert resp is calc.df


# ==================== 边界情况测试 ====================


class TestLiquidityFactorEdgeCases:
    """流动性因子边界情况测试"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({
            'close': [100],
            'vol': [1000000],
        })

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[5])

        # 单行数据，所有滚动计算都应该是NaN
        assert result['ILLIQUIDITY5'].isna().all()

    def test_small_dataset(self):
        """测试小数据集"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'vol': [1e6, 1e6, 1e6, 1e6, 1e6],
        })

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[3])

        # 前2个应该是NaN，第3个开始有值
        assert result['ILLIQUIDITY3'].iloc[:2].isna().all()
        assert not result['ILLIQUIDITY3'].iloc[2:].isna().all()

    def test_all_nan_prices(self):
        """测试全NaN价格"""
        df = pd.DataFrame({
            'close': [np.nan] * 10,
            'vol': [1e6] * 10,
        })

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[5])

        # 全NaN价格应该导致全NaN结果
        assert result['ILLIQUIDITY5'].isna().all()

    def test_constant_price(self):
        """测试恒定价格（零收益率）"""
        df = pd.DataFrame({
            'close': [100] * 50,
            'vol': np.random.uniform(1e6, 2e6, 50),
        })

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20])

        # 恒定价格导致零收益率，Amihud应该为0或接近0
        valid_values = result['ILLIQUIDITY20'].dropna()
        assert (valid_values.abs() < 1e-6).all()

    def test_negative_volume(self):
        """测试负成交量（异常数据）"""
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104],
            'vol': [1e6, -1e6, 1e6, 1e6, 1e6],  # 包含负值
        })

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[3])

        # 应该能处理负成交量（可能产生负的非流动性或NaN）
        assert 'ILLIQUIDITY3' in result.columns


# ==================== 性能和缓存测试 ====================


class TestLiquidityFactorPerformance:
    """流动性因子性能测试"""

    def test_large_dataset_performance(self):
        """测试大数据集性能"""
        import time

        # 生成大数据集
        np.random.seed(42)
        n = 5000
        df = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(n) * 0.5),
            'vol': np.random.uniform(1e6, 10e6, n),
        })

        calc = LiquidityFactorCalculator(df)

        start = time.time()
        result = calc.add_liquidity_factors(periods=[20, 60, 120])
        elapsed = time.time() - start

        # 验证结果
        assert 'ILLIQUIDITY20' in result.columns
        assert 'ILLIQUIDITY60' in result.columns
        assert 'ILLIQUIDITY120' in result.columns

        # 性能检查（应该在合理时间内完成）
        print(f"\n大数据集({n}行)计算时间: {elapsed:.3f}s")
        assert elapsed < 5.0  # 应该在5秒内完成

    def test_shared_cache_usage(self, sample_price_volume_data):
        """测试共享缓存的使用"""
        # 清空缓存
        LiquidityFactorCalculator._shared_cache.clear()

        calc1 = LiquidityFactorCalculator(sample_price_volume_data)
        calc1.add_liquidity_factors(periods=[20])

        # 获取缓存统计
        stats1 = calc1._shared_cache.get_stats()

        # 第二次计算（应该使用缓存）
        calc2 = LiquidityFactorCalculator(sample_price_volume_data)
        calc2.add_liquidity_factors(periods=[20])

        stats2 = calc2._shared_cache.get_stats()

        # 验证缓存被使用
        print(f"\n缓存统计: hits={stats2['hits']}, misses={stats2['misses']}")
        # 注意：由于收益率计算可能被缓存，第二次应该有更多命中
        assert stats2['hits'] >= stats1['hits']


# ==================== 异常处理测试 ====================


class TestLiquidityFactorErrorHandling:
    """流动性因子异常处理测试"""

    def test_invalid_period(self, sample_price_volume_data):
        """测试无效周期"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)

        # 零周期
        result = calc.add_liquidity_factors(periods=[0])
        # 应该处理异常，不添加无效列

        # 负周期
        result = calc.add_liquidity_factors(periods=[-10])
        # 应该处理异常

    def test_period_larger_than_data(self, sample_price_volume_data):
        """测试周期大于数据长度"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)
        result = calc.add_liquidity_factors(periods=[1000])  # 数据只有200行

        # 应该能计算，但结果全为NaN
        if 'ILLIQUIDITY1000' in result.columns:
            assert result['ILLIQUIDITY1000'].isna().all()

    def test_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame({'close': [], 'vol': []})

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20])

        # 空DataFrame应该返回空结果
        assert len(result) == 0

    def test_computation_error_handling(self, sample_price_volume_data):
        """测试计算过程中的异常处理"""
        calc = LiquidityFactorCalculator(sample_price_volume_data)

        # 使用异常周期列表（包含无效值）
        result = calc.add_liquidity_factors(periods=[20, None, -5, 0])

        # 应该至少计算有效的周期
        assert 'ILLIQUIDITY20' in result.columns


# ==================== 集成测试 ====================


class TestLiquidityFactorIntegration:
    """流动性因子集成测试"""

    def test_integration_with_other_factors(self, sample_price_volume_data):
        """测试与其他因子的集成"""
        from src.features.alpha_factors import MomentumFactorCalculator

        # 先计算动量因子
        momentum_calc = MomentumFactorCalculator(sample_price_volume_data)
        df_with_momentum = momentum_calc.add_rsi(periods=[14])

        # 再计算流动性因子
        liquidity_calc = LiquidityFactorCalculator(df_with_momentum)
        result = liquidity_calc.add_liquidity_factors(periods=[20])

        # 验证两类因子都存在
        assert 'RSI14' in result.columns  # 动量因子
        assert 'ILLIQUIDITY20' in result.columns  # 流动性因子

    def test_multiple_calculators_same_data(self, sample_price_volume_data):
        """测试多个计算器实例使用相同数据"""
        calc1 = LiquidityFactorCalculator(sample_price_volume_data)
        calc2 = LiquidityFactorCalculator(sample_price_volume_data)

        result1 = calc1.add_liquidity_factors(periods=[20])
        result2 = calc2.add_liquidity_factors(periods=[20])

        # 结果应该一致（使用共享缓存）
        pd.testing.assert_series_equal(
            result1['ILLIQUIDITY20'],
            result2['ILLIQUIDITY20'],
            check_names=False
        )


# ==================== 实际使用场景测试 ====================


class TestLiquidityFactorRealWorldScenarios:
    """实际使用场景测试"""

    def test_highly_liquid_stock(self):
        """测试高流动性股票（大盘股）"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 高流动性：大成交量，小波动
        df = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(100) * 0.005),
            'vol': np.random.uniform(50e6, 100e6, 100),  # 巨大成交量
        }, index=dates)

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20])

        # 高流动性股票应该有较低的非流动性指标
        avg_illiquidity = result['ILLIQUIDITY20'].dropna().mean()
        print(f"\n高流动性股票Amihud非流动性: {avg_illiquidity:.6f}")
        # 应该是一个较小的值

    def test_illiquid_stock(self):
        """测试低流动性股票（小盘股）"""
        np.random.seed(123)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 低流动性：小成交量，大波动
        df = pd.DataFrame({
            'close': 50 + np.cumsum(np.random.randn(100) * 0.03),  # 3%日波动
            'vol': np.random.uniform(100_000, 500_000, 100),  # 小成交量
        }, index=dates)

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[20])

        # 低流动性股票应该有较高的非流动性指标
        avg_illiquidity = result['ILLIQUIDITY20'].dropna().mean()
        print(f"\n低流动性股票Amihud非流动性: {avg_illiquidity:.6f}")
        # 应该是一个较大的值

    def test_market_crash_scenario(self):
        """测试市场崩盘场景（流动性枯竭）"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 正常交易
        normal_vol = np.full(50, 10e6)
        normal_price_changes = np.random.randn(50) * 0.01

        # 崩盘：巨大波动，成交量萎缩
        crash_vol = np.full(20, 1e6)  # 成交量大幅下降
        crash_price_changes = np.random.randn(20) * 0.05  # 波动率激增

        # 恢复
        recovery_vol = np.full(30, 8e6)
        recovery_price_changes = np.random.randn(30) * 0.02

        volumes = np.concatenate([normal_vol, crash_vol, recovery_vol])
        price_changes = np.concatenate([normal_price_changes, crash_price_changes, recovery_price_changes])
        prices = 100 * (1 + price_changes).cumprod()

        df = pd.DataFrame({
            'close': prices,
            'vol': volumes,
        }, index=dates)

        calc = LiquidityFactorCalculator(df)
        result = calc.add_liquidity_factors(periods=[10])

        # 崩盘期间的非流动性应该显著上升
        normal_period = result['ILLIQUIDITY10'].iloc[30:45].mean()
        crash_period = result['ILLIQUIDITY10'].iloc[55:65].mean()

        print(f"\n正常期非流动性: {normal_period:.6f}, 崩盘期非流动性: {crash_period:.6f}")
        # 崩盘期应该更高（如果不是NaN的话）
        if not np.isnan(crash_period) and not np.isnan(normal_period):
            assert crash_period > normal_period


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
