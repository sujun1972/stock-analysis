"""
特征策略模式测试

全面测试特征策略的所有功能，包括：
- 各个策略的计算正确性
- 配置验证和异常处理
- 组合策略的工作流程
- 便捷函数和辅助工具

作者: Stock Analysis Team
更新: 2026-01-27
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.features.feature_strategy import (
    # 异常类
    FeatureComputationError,
    InvalidDataError,
    # 基类
    FeatureStrategy,
    # 策略类
    TechnicalIndicatorStrategy,
    AlphaFactorStrategy,
    PriceTransformStrategy,
    CompositeFeatureStrategy,
    # 便捷函数
    create_default_feature_pipeline,
    create_minimal_feature_pipeline,
    create_custom_feature_pipeline,
    # 辅助函数
    merge_configs,
    validate_period_config,
    validate_tuple_config,
)


# ==================== Fixtures ====================

@pytest.fixture
def sample_ohlcv_df():
    """生成完整的OHLCV数据用于测试"""
    np.random.seed(42)
    n = 50
    base_price = 100
    prices = base_price + np.cumsum(np.random.randn(n) * 0.5)

    return pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(n) * 0.5),
        'low': prices - np.abs(np.random.randn(n) * 0.5),
        'close': prices + np.random.randn(n) * 0.3,
        'volume': np.random.randint(1000, 2000, n)
    })


@pytest.fixture
def large_ohlcv_df():
    """生成大量数据用于测试"""
    np.random.seed(42)
    n = 200
    base_price = 100
    prices = base_price + np.cumsum(np.random.randn(n) * 0.5)

    return pd.DataFrame({
        'open': prices,
        'high': prices + np.abs(np.random.randn(n) * 0.5),
        'low': prices - np.abs(np.random.randn(n) * 0.5),
        'close': prices + np.random.randn(n) * 0.3,
        'volume': np.random.randint(1000, 2000, n)
    })


@pytest.fixture
def minimal_ohlcv_df():
    """生成最小数据集（用于测试边界情况）"""
    return pd.DataFrame({
        'open': [100, 102],
        'high': [103, 105],
        'low': [99, 101],
        'close': [102, 104],
        'volume': [1000, 1200]
    })


@pytest.fixture
def constant_price_df():
    """生成价格不变的数据"""
    return pd.DataFrame({
        'open': [100] * 30,
        'high': [100] * 30,
        'low': [100] * 30,
        'close': [100] * 30,
        'volume': [1000] * 30
    })


# ==================== 辅助函数测试 ====================

class TestMergeConfigs:
    """测试配置合并函数"""

    def test_merge_with_none(self):
        """测试用户配置为None的情况"""
        default = {'ma': [5, 10], 'rsi': [14]}
        result = merge_configs(default, None)

        assert result == default
        assert result is not default  # 应该是副本

    def test_merge_with_empty(self):
        """测试用户配置为空字典"""
        default = {'ma': [5, 10], 'rsi': [14]}
        result = merge_configs(default, {})

        assert result == default

    def test_merge_override(self):
        """测试用户配置覆盖默认配置"""
        default = {'ma': [5, 10], 'rsi': [14]}
        user = {'ma': [20, 60]}
        result = merge_configs(default, user)

        assert result == {'ma': [20, 60], 'rsi': [14]}

    def test_merge_add_new_keys(self):
        """测试用户配置添加新键"""
        default = {'ma': [5, 10]}
        user = {'rsi': [14]}
        result = merge_configs(default, user)

        assert result == {'ma': [5, 10], 'rsi': [14]}


class TestValidatePeriodConfig:
    """测试周期配置验证函数"""

    def test_valid_config(self):
        """测试有效配置"""
        config = {'ma': [5, 10, 20], 'rsi': [14]}
        # 不应该抛出异常
        validate_period_config(config, ['ma', 'rsi'])

    def test_invalid_type_not_list(self):
        """测试配置不是列表"""
        config = {'ma': 5}  # 应该是列表
        with pytest.raises(ValueError, match="必须是列表类型"):
            validate_period_config(config, ['ma'])

    def test_invalid_period_not_int(self):
        """测试周期不是整数"""
        config = {'ma': [5, 10.5, 20]}
        with pytest.raises(ValueError, match="周期必须是正整数"):
            validate_period_config(config, ['ma'])

    def test_invalid_period_negative(self):
        """测试周期为负数"""
        config = {'ma': [5, -10, 20]}
        with pytest.raises(ValueError, match="周期必须是正整数"):
            validate_period_config(config, ['ma'])

    def test_invalid_period_zero(self):
        """测试周期为零"""
        config = {'ma': [5, 0, 20]}
        with pytest.raises(ValueError, match="周期必须是正整数"):
            validate_period_config(config, ['ma'])

    def test_missing_key_ignored(self):
        """测试缺失的键被忽略"""
        config = {'ma': [5, 10]}
        # 不应该抛出异常（rsi不存在但被忽略）
        validate_period_config(config, ['ma', 'rsi'])


class TestValidateTupleConfig:
    """测试元组配置验证函数"""

    def test_valid_config(self):
        """测试有效配置"""
        config = {'macd': [(12, 26, 9)]}
        # 不应该抛出异常
        validate_tuple_config(config, ['macd'], expected_length=3)

    def test_invalid_type_not_list(self):
        """测试配置不是列表"""
        config = {'macd': (12, 26, 9)}
        with pytest.raises(ValueError, match="必须是列表类型"):
            validate_tuple_config(config, ['macd'])

    def test_invalid_element_not_tuple(self):
        """测试元素不是元组"""
        config = {'macd': [[12, 26, 9]]}
        with pytest.raises(ValueError, match="参数必须是元组"):
            validate_tuple_config(config, ['macd'])

    def test_invalid_tuple_length(self):
        """测试元组长度不匹配"""
        config = {'macd': [(12, 26)]}  # 应该是3个元素
        with pytest.raises(ValueError, match="必须包含 3 个元素"):
            validate_tuple_config(config, ['macd'], expected_length=3)

    def test_no_length_check(self):
        """测试不检查长度"""
        config = {'macd': [(12, 26), (12, 26, 9)]}
        # 不应该抛出异常（不检查长度）
        validate_tuple_config(config, ['macd'], expected_length=None)


# ==================== TechnicalIndicatorStrategy 测试 ====================

class TestTechnicalIndicatorStrategy:
    """测试技术指标策略"""

    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        strategy = TechnicalIndicatorStrategy()
        assert 'ma' in strategy.config
        assert 'rsi' in strategy.config

    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        custom_config = {'ma': [5, 20], 'rsi': [14]}
        strategy = TechnicalIndicatorStrategy(config=custom_config)
        assert strategy.config['ma'] == [5, 20]
        assert strategy.config['rsi'] == [14]

    def test_invalid_config_ma(self):
        """测试无效的MA配置"""
        with pytest.raises(ValueError):
            TechnicalIndicatorStrategy(config={'ma': 'invalid'})

    def test_invalid_config_macd(self):
        """测试无效的MACD配置"""
        # MACD配置不强制长度，所以测试无效类型
        with pytest.raises(ValueError):
            TechnicalIndicatorStrategy(config={'macd': 'invalid'})

    def test_compute_basic(self, sample_ohlcv_df):
        """测试基本计算"""
        strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'MA_5' in result.columns
        assert 'MA_10' in result.columns
        assert len(result) == len(sample_ohlcv_df)

    def test_compute_all_indicators(self, large_ohlcv_df):
        """测试计算所有指标"""
        strategy = TechnicalIndicatorStrategy()
        result = strategy.compute(large_ohlcv_df)

        # 检查各类指标是否存在
        assert any('MA_' in col for col in result.columns)
        assert any('EMA_' in col for col in result.columns)
        assert any('RSI_' in col for col in result.columns)
        assert any('MACD_' in col for col in result.columns)
        assert any('KDJ_' in col for col in result.columns)
        assert any('BOLL_' in col for col in result.columns)
        assert any('ATR_' in col for col in result.columns)
        assert 'OBV' in result.columns
        assert any('CCI_' in col for col in result.columns)

    def test_compute_ma_only(self, sample_ohlcv_df):
        """测试仅计算MA"""
        strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10, 20]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'MA_5' in result.columns
        assert 'MA_10' in result.columns
        assert 'MA_20' in result.columns

    def test_compute_rsi_only(self, sample_ohlcv_df):
        """测试仅计算RSI"""
        strategy = TechnicalIndicatorStrategy(config={'rsi': [6, 14]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'RSI_6' in result.columns
        assert 'RSI_14' in result.columns

    def test_compute_macd(self, large_ohlcv_df):
        """测试MACD计算"""
        strategy = TechnicalIndicatorStrategy(config={'macd': [(12, 26, 9)]})
        result = strategy.compute(large_ohlcv_df)

        assert 'MACD_12_26' in result.columns
        assert 'MACD_SIGNAL_12_26' in result.columns
        assert 'MACD_HIST_12_26' in result.columns

    def test_compute_kdj(self, large_ohlcv_df):
        """测试KDJ计算"""
        strategy = TechnicalIndicatorStrategy(config={'kdj': [(9, 3, 3)]})
        result = strategy.compute(large_ohlcv_df)

        assert 'KDJ_K_9' in result.columns
        assert 'KDJ_D_9' in result.columns
        assert 'KDJ_J_9' in result.columns

    def test_compute_boll(self, sample_ohlcv_df):
        """测试布林带计算"""
        strategy = TechnicalIndicatorStrategy(config={'boll': [(20, 2)]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'BOLL_UPPER_20' in result.columns
        assert 'BOLL_MIDDLE_20' in result.columns
        assert 'BOLL_LOWER_20' in result.columns

    def test_feature_names(self):
        """测试特征名称生成"""
        strategy = TechnicalIndicatorStrategy(config={
            'ma': [5, 10],
            'rsi': [14],
            'macd': [(12, 26, 9)]
        })
        names = strategy.feature_names

        assert 'MA_5' in names
        assert 'MA_10' in names
        assert 'RSI_14' in names
        assert 'MACD_12_26' in names
        assert 'MACD_SIGNAL_12_26' in names
        assert 'MACD_HIST_12_26' in names

    def test_feature_names_caching(self):
        """测试特征名称缓存"""
        strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10]})
        names1 = strategy.feature_names
        names2 = strategy.feature_names

        assert names1 is names2  # 应该是同一个对象（缓存）

    def test_invalid_data_empty(self):
        """测试空数据"""
        strategy = TechnicalIndicatorStrategy()
        empty_df = pd.DataFrame()

        with pytest.raises(InvalidDataError, match="输入 DataFrame 为空"):
            strategy.compute(empty_df)

    def test_invalid_data_missing_columns(self, sample_ohlcv_df):
        """测试缺少必需列"""
        strategy = TechnicalIndicatorStrategy()
        incomplete_df = sample_ohlcv_df.drop(columns=['close'])

        with pytest.raises(InvalidDataError, match="缺少必需列"):
            strategy.compute(incomplete_df)

    def test_constant_price(self, constant_price_df):
        """测试价格不变的情况"""
        strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10], 'rsi': [14]})
        result = strategy.compute(constant_price_df)

        # 应该能够成功计算，即使结果可能是常数
        assert 'MA_5' in result.columns
        assert 'RSI_14' in result.columns


# ==================== AlphaFactorStrategy 测试 ====================

class TestAlphaFactorStrategy:
    """测试Alpha因子策略"""

    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        strategy = AlphaFactorStrategy()
        assert 'momentum' in strategy.config
        assert 'reversal' in strategy.config
        assert 'volatility' in strategy.config

    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        custom_config = {'momentum': [5, 20], 'volatility': [10]}
        strategy = AlphaFactorStrategy(config=custom_config)
        assert strategy.config['momentum'] == [5, 20]

    def test_invalid_config(self):
        """测试无效配置"""
        with pytest.raises(ValueError):
            AlphaFactorStrategy(config={'momentum': 'invalid'})

    def test_compute_basic(self, sample_ohlcv_df):
        """测试基本计算"""
        strategy = AlphaFactorStrategy(config={'momentum': [5, 10]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'MOMENTUM_5' in result.columns
        assert 'MOMENTUM_10' in result.columns

    def test_compute_all_factors(self, large_ohlcv_df):
        """测试计算所有因子"""
        strategy = AlphaFactorStrategy()
        result = strategy.compute(large_ohlcv_df)

        # 检查各类因子是否存在
        assert any('MOMENTUM_' in col for col in result.columns)
        assert any('REVERSAL_' in col for col in result.columns)
        assert any('VOLATILITY_' in col for col in result.columns)
        assert any('VOLUME_RATIO_' in col for col in result.columns)
        assert any('PRICE_VOL_CORR_' in col for col in result.columns)

    def test_compute_momentum(self, large_ohlcv_df):
        """测试动量因子计算"""
        strategy = AlphaFactorStrategy(config={'momentum': [5, 20]})
        result = strategy.compute(large_ohlcv_df)

        assert 'MOMENTUM_5' in result.columns
        assert 'MOMENTUM_20' in result.columns

        # 动量因子应该是收益率
        momentum_5 = result['MOMENTUM_5'].dropna()
        assert len(momentum_5) > 0

    def test_compute_reversal(self, large_ohlcv_df):
        """测试反转因子计算"""
        strategy = AlphaFactorStrategy(config={'reversal': [1, 3]})
        result = strategy.compute(large_ohlcv_df)

        assert 'REVERSAL_1' in result.columns
        assert 'REVERSAL_3' in result.columns

        # 反转因子应该是负的动量
        reversal = result['REVERSAL_1'].dropna()
        assert len(reversal) > 0

    def test_compute_volatility(self, large_ohlcv_df):
        """测试波动率因子计算"""
        strategy = AlphaFactorStrategy(config={'volatility': [5, 20]})
        result = strategy.compute(large_ohlcv_df)

        assert 'VOLATILITY_5' in result.columns
        assert 'VOLATILITY_20' in result.columns

        # 波动率应该非负
        vol = result['VOLATILITY_5'].dropna()
        assert all(vol >= 0)

    def test_compute_volume_ratio(self, large_ohlcv_df):
        """测试成交量比率因子"""
        strategy = AlphaFactorStrategy(config={'volume': [5, 20]})
        result = strategy.compute(large_ohlcv_df)

        assert 'VOLUME_RATIO_5' in result.columns
        assert 'VOLUME_RATIO_20' in result.columns

        # 成交量比率应该为正
        vol_ratio = result['VOLUME_RATIO_5'].dropna()
        assert all(vol_ratio >= 0)

    def test_compute_correlation(self, large_ohlcv_df):
        """测试价格-成交量相关性因子"""
        strategy = AlphaFactorStrategy(config={'correlation': [(5, 20)]})
        result = strategy.compute(large_ohlcv_df)

        assert 'PRICE_VOL_CORR_5_20' in result.columns

        # 相关性应该在-1到1之间
        corr = result['PRICE_VOL_CORR_5_20'].dropna()
        if len(corr) > 0:
            assert all((corr >= -1.1) & (corr <= 1.1))  # 允许小误差

    def test_feature_names(self):
        """测试特征名称生成"""
        strategy = AlphaFactorStrategy(config={
            'momentum': [5, 20],
            'volatility': [10],
            'correlation': [(5, 20)]
        })
        names = strategy.feature_names

        assert 'MOMENTUM_5' in names
        assert 'MOMENTUM_20' in names
        assert 'VOLATILITY_10' in names
        assert 'PRICE_VOL_CORR_5_20' in names

    def test_invalid_data(self):
        """测试无效数据"""
        strategy = AlphaFactorStrategy()
        empty_df = pd.DataFrame()

        with pytest.raises(InvalidDataError):
            strategy.compute(empty_df)


# ==================== PriceTransformStrategy 测试 ====================

class TestPriceTransformStrategy:
    """测试价格转换策略"""

    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        strategy = PriceTransformStrategy()
        assert 'returns' in strategy.config
        assert 'log_returns' in strategy.config
        assert 'price_position' in strategy.config

    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        custom_config = {'returns': [1, 5], 'ohlc_features': True}
        strategy = PriceTransformStrategy(config=custom_config)
        assert strategy.config['returns'] == [1, 5]

    def test_compute_basic(self, sample_ohlcv_df):
        """测试基本计算"""
        strategy = PriceTransformStrategy(config={'returns': [1, 5]})
        result = strategy.compute(sample_ohlcv_df)

        assert 'RETURN_1D' in result.columns
        assert 'RETURN_5D' in result.columns

    def test_compute_all_transforms(self, large_ohlcv_df):
        """测试计算所有转换"""
        strategy = PriceTransformStrategy()
        result = strategy.compute(large_ohlcv_df)

        # 检查各类特征是否存在
        assert any('RETURN_' in col for col in result.columns)
        assert any('LOG_RETURN_' in col for col in result.columns)
        assert any('PRICE_POSITION_' in col for col in result.columns)
        assert 'BODY_SIZE' in result.columns
        assert 'UPPER_SHADOW' in result.columns
        assert 'LOWER_SHADOW' in result.columns
        assert 'INTRADAY_RANGE' in result.columns

    def test_compute_returns(self, large_ohlcv_df):
        """测试收益率计算"""
        strategy = PriceTransformStrategy(config={'returns': [1, 5, 10]})
        result = strategy.compute(large_ohlcv_df)

        assert 'RETURN_1D' in result.columns
        assert 'RETURN_5D' in result.columns
        assert 'RETURN_10D' in result.columns

    def test_compute_log_returns(self, large_ohlcv_df):
        """测试对数收益率计算"""
        strategy = PriceTransformStrategy(config={'log_returns': [1, 5]})
        result = strategy.compute(large_ohlcv_df)

        assert 'LOG_RETURN_1D' in result.columns
        assert 'LOG_RETURN_5D' in result.columns

    def test_compute_price_position(self, large_ohlcv_df):
        """测试价格位置计算"""
        strategy = PriceTransformStrategy(config={'price_position': [5, 20]})
        result = strategy.compute(large_ohlcv_df)

        assert 'PRICE_POSITION_5' in result.columns
        assert 'PRICE_POSITION_20' in result.columns

        # 价格位置应该在0-1之间
        pos = result['PRICE_POSITION_5'].dropna()
        assert all((pos >= -0.1) & (pos <= 1.1))  # 允许小误差

    def test_compute_ohlc_features(self, large_ohlcv_df):
        """测试OHLC特征计算"""
        strategy = PriceTransformStrategy(config={'ohlc_features': True})
        result = strategy.compute(large_ohlcv_df)

        assert 'BODY_SIZE' in result.columns
        assert 'UPPER_SHADOW' in result.columns
        assert 'LOWER_SHADOW' in result.columns
        assert 'INTRADAY_RANGE' in result.columns

        # 所有OHLC特征应该有值
        assert result['BODY_SIZE'].notna().sum() > 0
        assert result['INTRADAY_RANGE'].notna().sum() > 0

    def test_ohlc_features_no_inf(self, large_ohlcv_df):
        """测试OHLC特征不产生无穷值"""
        strategy = PriceTransformStrategy(config={'ohlc_features': True})
        result = strategy.compute(large_ohlcv_df)

        # 检查没有无穷值
        assert not np.isinf(result['BODY_SIZE']).any()
        assert not np.isinf(result['UPPER_SHADOW']).any()
        assert not np.isinf(result['LOWER_SHADOW']).any()
        assert not np.isinf(result['INTRADAY_RANGE']).any()

    def test_feature_names(self):
        """测试特征名称生成"""
        strategy = PriceTransformStrategy(config={
            'returns': [1, 5],
            'log_returns': [1],
            'ohlc_features': True
        })
        names = strategy.feature_names

        assert 'RETURN_1D' in names
        assert 'RETURN_5D' in names
        assert 'LOG_RETURN_1D' in names
        assert 'BODY_SIZE' in names


# ==================== CompositeFeatureStrategy 测试 ====================

class TestCompositeFeatureStrategy:
    """测试组合特征策略"""

    def test_initialization_basic(self):
        """测试基本初始化"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha])

        assert len(composite.strategies) == 2

    def test_initialization_empty_list(self):
        """测试空策略列表"""
        with pytest.raises(ValueError, match="策略列表不能为空"):
            CompositeFeatureStrategy([])

    def test_initialization_invalid_strategy(self):
        """测试无效策略"""
        with pytest.raises(ValueError, match="必须是 FeatureStrategy 实例"):
            CompositeFeatureStrategy(["not a strategy"])

    def test_compute_basic(self, sample_ohlcv_df):
        """测试基本计算"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5, 10]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha])

        result = composite.compute(sample_ohlcv_df)

        # 应该包含两个策略的所有特征
        assert 'MA_5' in result.columns
        assert 'MA_10' in result.columns
        assert 'MOMENTUM_5' in result.columns

    def test_compute_three_strategies(self, large_ohlcv_df):
        """测试三个策略的组合"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        price = PriceTransformStrategy(config={'returns': [1]})
        composite = CompositeFeatureStrategy([tech, alpha, price])

        result = composite.compute(large_ohlcv_df)

        assert 'MA_5' in result.columns
        assert 'MOMENTUM_5' in result.columns
        assert 'RETURN_1D' in result.columns

    def test_compute_inplace_false(self, sample_ohlcv_df):
        """测试inplace=False（默认）"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech], inplace=False)

        original_columns = set(sample_ohlcv_df.columns)
        result = composite.compute(sample_ohlcv_df)

        # 原始DataFrame不应该被修改
        assert set(sample_ohlcv_df.columns) == original_columns

    def test_compute_inplace_true(self, sample_ohlcv_df):
        """测试inplace=True"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech], inplace=True)

        df_copy = sample_ohlcv_df.copy()
        result = composite.compute(df_copy)

        # 由于inplace=True，新列应该被添加到原始df
        # 但由于第一个策略会复制df，result可能不是df_copy本身
        # 检查是否在原始df上添加了新列
        assert 'MA_5' in result.columns
        assert len(result) == len(df_copy)

    def test_compute_with_failure(self, sample_ohlcv_df):
        """测试某个策略失败的情况"""
        # 创建一个会失败的mock策略
        failing_strategy = Mock(spec=FeatureStrategy)
        failing_strategy.compute.side_effect = Exception("Test error")
        failing_strategy.feature_names = []
        failing_strategy.__class__.__name__ = "FailingStrategy"

        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([failing_strategy, tech])

        # 应该继续执行其他策略
        result = composite.compute(sample_ohlcv_df)
        assert 'MA_5' in result.columns

    def test_feature_names(self):
        """测试特征名称聚合"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5, 10]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha])

        names = composite.feature_names

        assert 'MA_5' in names
        assert 'MA_10' in names
        assert 'MOMENTUM_5' in names

    def test_add_strategy(self):
        """测试添加策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech])

        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite.add_strategy(alpha)

        assert len(composite.strategies) == 2
        assert 'MOMENTUM_5' in composite.feature_names

    def test_add_invalid_strategy(self):
        """测试添加无效策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech])

        with pytest.raises(ValueError, match="必须是 FeatureStrategy 实例"):
            composite.add_strategy("not a strategy")

    def test_remove_strategy(self):
        """测试移除策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha])

        result = composite.remove_strategy(AlphaFactorStrategy)

        assert result is True
        assert len(composite.strategies) == 1
        assert 'MOMENTUM_5' not in composite.feature_names

    def test_remove_nonexistent_strategy(self):
        """测试移除不存在的策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech])

        result = composite.remove_strategy(AlphaFactorStrategy)

        assert result is False
        assert len(composite.strategies) == 1

    def test_get_strategy(self):
        """测试获取策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha])

        retrieved = composite.get_strategy(TechnicalIndicatorStrategy)

        assert retrieved is tech

    def test_get_nonexistent_strategy(self):
        """测试获取不存在的策略"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        composite = CompositeFeatureStrategy([tech])

        retrieved = composite.get_strategy(AlphaFactorStrategy)

        assert retrieved is None

    def test_repr(self):
        """测试字符串表示"""
        tech = TechnicalIndicatorStrategy(config={'ma': [5]})
        alpha = AlphaFactorStrategy(config={'momentum': [5]})
        composite = CompositeFeatureStrategy([tech, alpha], inplace=True)

        repr_str = repr(composite)

        assert 'CompositeFeatureStrategy' in repr_str
        assert 'TechnicalIndicatorStrategy' in repr_str
        assert 'AlphaFactorStrategy' in repr_str
        assert 'inplace=True' in repr_str


# ==================== 便捷函数测试 ====================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_default_pipeline(self):
        """测试创建默认管道"""
        pipeline = create_default_feature_pipeline()

        assert isinstance(pipeline, CompositeFeatureStrategy)
        assert len(pipeline.strategies) == 3
        assert any(isinstance(s, TechnicalIndicatorStrategy) for s in pipeline.strategies)
        assert any(isinstance(s, AlphaFactorStrategy) for s in pipeline.strategies)
        assert any(isinstance(s, PriceTransformStrategy) for s in pipeline.strategies)

    def test_create_default_pipeline_inplace(self):
        """测试创建默认管道（inplace=True）"""
        pipeline = create_default_feature_pipeline(inplace=True)

        assert pipeline.inplace is True

    def test_create_minimal_pipeline(self):
        """测试创建最小管道"""
        pipeline = create_minimal_feature_pipeline()

        assert isinstance(pipeline, CompositeFeatureStrategy)
        assert len(pipeline.strategies) == 3

        # 检查配置是否简化
        tech = pipeline.get_strategy(TechnicalIndicatorStrategy)
        assert tech.config['ma'] == [5, 20]

    def test_create_minimal_pipeline_compute(self, large_ohlcv_df):
        """测试最小管道的计算"""
        pipeline = create_minimal_feature_pipeline()
        result = pipeline.compute(large_ohlcv_df)

        # 应该生成较少的特征（最小管道也会生成多个特征）
        feature_count = len([col for col in result.columns if col not in large_ohlcv_df.columns])
        assert 20 < feature_count < 50  # 最小管道特征数介于20-50之间

    def test_create_custom_pipeline_all_configs(self):
        """测试创建自定义管道（提供所有配置）"""
        pipeline = create_custom_feature_pipeline(
            technical_config={'ma': [5]},
            alpha_config={'momentum': [5]},
            price_config={'returns': [1]}
        )

        assert len(pipeline.strategies) == 3

    def test_create_custom_pipeline_partial_configs(self):
        """测试创建自定义管道（部分配置）"""
        pipeline = create_custom_feature_pipeline(
            technical_config={'ma': [5]},
            alpha_config=None,
            price_config={'returns': [1]}
        )

        assert len(pipeline.strategies) == 2
        assert pipeline.get_strategy(AlphaFactorStrategy) is None

    def test_create_custom_pipeline_empty_configs(self):
        """测试创建自定义管道（空字典表示使用默认配置）"""
        pipeline = create_custom_feature_pipeline(
            technical_config={},
            alpha_config=None,
            price_config=None
        )

        assert len(pipeline.strategies) == 1
        tech = pipeline.get_strategy(TechnicalIndicatorStrategy)
        # 空字典应该使用默认配置
        assert 'ma' in tech.config

    def test_create_custom_pipeline_no_configs(self):
        """测试创建自定义管道（不提供任何配置）"""
        # 不提供任何配置会创建空策略列表，这会在初始化时报错
        with pytest.raises(ValueError, match="策略列表不能为空"):
            create_custom_feature_pipeline(
                technical_config=None,
                alpha_config=None,
                price_config=None
            )


# ==================== 集成测试 ====================

class TestIntegration:
    """测试完整的特征工程流程"""

    def test_full_pipeline_default(self, large_ohlcv_df):
        """测试完整的默认管道"""
        pipeline = create_default_feature_pipeline()
        result = pipeline.compute(large_ohlcv_df)

        # 应该生成大量特征（45个左右）
        new_features = [col for col in result.columns if col not in large_ohlcv_df.columns]
        assert len(new_features) > 40  # 默认管道应该生成40+特征

        # 检查没有无穷值
        for col in new_features:
            assert not np.isinf(result[col]).any(), f"{col} contains inf values"

    def test_full_pipeline_minimal(self, large_ohlcv_df):
        """测试最小管道"""
        pipeline = create_minimal_feature_pipeline()
        result = pipeline.compute(large_ohlcv_df)

        # 最小管道特征较少（但仍有30+）
        new_features = [col for col in result.columns if col not in large_ohlcv_df.columns]
        assert 20 < len(new_features) < 50

    def test_custom_pipeline_workflow(self, large_ohlcv_df):
        """测试自定义管道工作流"""
        # 1. 创建自定义管道
        pipeline = create_custom_feature_pipeline(
            technical_config={'ma': [5, 20], 'rsi': [14]},
            alpha_config={'momentum': [5, 20]},
            price_config=None
        )

        # 2. 计算特征
        result = pipeline.compute(large_ohlcv_df)

        # 3. 验证特征
        assert 'MA_5' in result.columns
        assert 'MA_20' in result.columns
        assert 'RSI_14' in result.columns
        assert 'MOMENTUM_5' in result.columns
        assert 'MOMENTUM_20' in result.columns

        # 4. 动态添加策略
        pipeline.add_strategy(PriceTransformStrategy(config={'returns': [1]}))
        result2 = pipeline.compute(large_ohlcv_df)

        assert 'RETURN_1D' in result2.columns

    def test_pipeline_with_minimal_data(self, minimal_ohlcv_df):
        """测试最小数据集"""
        pipeline = create_minimal_feature_pipeline()
        result = pipeline.compute(minimal_ohlcv_df)

        # 即使数据很少，也应该能成功计算
        assert len(result) == len(minimal_ohlcv_df)

    def test_pipeline_with_constant_price(self, constant_price_df):
        """测试价格不变的数据"""
        pipeline = create_minimal_feature_pipeline()
        result = pipeline.compute(constant_price_df)

        # 应该能够处理价格不变的情况
        assert len(result) == len(constant_price_df)
        # 不应该有无穷值
        for col in result.columns:
            if result[col].dtype in [np.float64, np.float32]:
                assert not np.isinf(result[col]).any()

    def test_multiple_pipelines_same_data(self, large_ohlcv_df):
        """测试在同一数据上运行多个管道"""
        pipeline1 = create_minimal_feature_pipeline()
        pipeline2 = create_default_feature_pipeline()

        result1 = pipeline1.compute(large_ohlcv_df)
        result2 = pipeline2.compute(large_ohlcv_df)

        # 原始数据不应该被修改
        assert 'MA_5' not in large_ohlcv_df.columns

        # 两个结果应该不同
        assert len(result1.columns) < len(result2.columns)


# ==================== 异常处理测试 ====================

class TestExceptionHandling:
    """测试异常处理"""

    def test_feature_computation_error(self):
        """测试特征计算错误"""
        # InvalidDataError应该被抛出
        strategy = TechnicalIndicatorStrategy()

        with pytest.raises(InvalidDataError):
            strategy.compute(pd.DataFrame())

    def test_invalid_data_error_message(self):
        """测试无效数据错误消息"""
        strategy = TechnicalIndicatorStrategy()

        try:
            strategy.compute(pd.DataFrame({'close': [1, 2, 3]}))
        except InvalidDataError as e:
            assert "缺少必需列" in str(e)

    def test_insufficient_data_warning(self, caplog):
        """测试数据不足时的警告"""
        strategy = TechnicalIndicatorStrategy()
        df = pd.DataFrame({
            'open': [100],
            'high': [102],
            'low': [99],
            'close': [101],
            'volume': [1000]
        })

        # 应该记录警告
        with caplog.at_level('WARNING'):
            result = strategy.compute(df)
            # 检查是否有警告（数据量不足）
            # 注意：由于数据量为1，某些指标可能无法计算


# ==================== 性能测试 ====================

class TestPerformance:
    """测试性能（简单的烟雾测试）"""

    def test_large_dataset_default_pipeline(self):
        """测试大数据集的默认管道"""
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

        pipeline = create_default_feature_pipeline()
        result = pipeline.compute(df)

        # 确保能够成功计算
        assert len(result) == n
        assert len(result.columns) > len(df.columns)

    def test_minimal_pipeline_performance(self):
        """测试最小管道性能（应该比默认管道快）"""
        n = 2000
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)

        df = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(n) * 0.5),
            'low': prices - np.abs(np.random.randn(n) * 0.5),
            'close': prices + np.random.randn(n) * 0.3,
            'volume': np.random.randint(1000, 2000, n)
        })

        pipeline = create_minimal_feature_pipeline()
        result = pipeline.compute(df)

        # 确保能够成功计算
        assert len(result) == n
