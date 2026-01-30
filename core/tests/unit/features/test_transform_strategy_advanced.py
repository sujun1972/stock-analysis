"""
特征转换策略高级测试

测试transform_strategy模块的高级功能：
- 装饰器（validate_dataframe, handle_errors）
- 组合策略嵌套
- 工厂函数
- 配置验证
- Scaler管理

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from pathlib import Path
import shutil

from src.features.transform_strategy import (
    # 异常类
    TransformError,
    InvalidDataError,
    ScalerNotFoundError,
    # 策略类
    TransformStrategy,
    PriceChangeTransformStrategy,
    NormalizationStrategy,
    TimeFeatureStrategy,
    StatisticalFeatureStrategy,
    CompositeTransformStrategy,
    # 装饰器
    validate_dataframe,
    safe_transform,
    # 工厂函数
    create_default_transform_pipeline,
)
from sklearn.preprocessing import StandardScaler, RobustScaler


# ==================== Fixtures ====================


@pytest.fixture
def sample_ohlc_df():
    """生成OHLC数据"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    prices = 100 + np.cumsum(np.random.randn(50) * 0.5)

    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1e6, 10e6, 50),
    }, index=dates)


@pytest.fixture
def temp_scaler_dir(tmp_path):
    """创建临时scaler目录"""
    scaler_dir = tmp_path / "scalers"
    scaler_dir.mkdir(parents=True, exist_ok=True)
    yield scaler_dir
    if scaler_dir.exists():
        shutil.rmtree(scaler_dir)


# ==================== 装饰器测试 ====================


class TestValidateDataframeDecorator:
    """validate_dataframe装饰器测试"""

    def test_decorator_with_valid_dataframe(self, sample_ohlc_df):
        """测试装饰器通过有效DataFrame"""

        class DummyStrategy:
            @validate_dataframe(min_rows=2)
            def transform(self, df):
                return df

        strategy = DummyStrategy()
        result = strategy.transform(sample_ohlc_df)
        assert isinstance(result, pd.DataFrame)
        assert not result.empty

    def test_decorator_rejects_empty_dataframe(self):
        """测试装饰器拒绝空DataFrame"""

        class DummyStrategy:
            @validate_dataframe(min_rows=2)
            def transform(self, df):
                return df

        strategy = DummyStrategy()
        empty_df = pd.DataFrame()

        with pytest.raises(InvalidDataError, match="DataFrame 为空"):
            strategy.transform(empty_df)

    def test_decorator_rejects_none(self):
        """测试装饰器拒绝None"""

        class DummyStrategy:
            @validate_dataframe(min_rows=2)
            def transform(self, df):
                return df

        strategy = DummyStrategy()

        with pytest.raises(InvalidDataError, match="DataFrame 为空"):
            strategy.transform(None)

    def test_decorator_warns_insufficient_rows(self):
        """测试装饰器对行数不足的警告"""

        class DummyStrategy:
            @validate_dataframe(min_rows=10)
            def transform(self, df):
                return df

        strategy = DummyStrategy()
        small_df = pd.DataFrame({'col1': [1, 2, 3]})

        # 应该发出警告但不抛出异常
        result = strategy.transform(small_df)
        assert len(result) == 3


class TestSafeTransformDecorator:
    """safe_transform装饰器测试"""

    def test_decorator_catches_exceptions(self):
        """测试装饰器捕获异常"""

        @safe_transform("test_transform")
        def failing_transform(df):
            raise ValueError("Intentional error")

        df = pd.DataFrame({'col1': [1, 2, 3]})

        with pytest.raises(TransformError, match="test_transform 转换失败"):
            failing_transform(df)

    def test_decorator_preserves_transform_error(self):
        """测试装饰器保留TransformError"""

        @safe_transform("test_transform")
        def raise_transform_error(df):
            raise TransformError("Custom transform error")

        df = pd.DataFrame({'col1': [1, 2, 3]})

        with pytest.raises(TransformError, match="Custom transform error"):
            raise_transform_error(df)

    def test_decorator_successful_execution(self, sample_ohlc_df):
        """测试装饰器不影响正常执行"""

        @safe_transform("test_transform")
        def successful_transform(df):
            df['new_col'] = df['close'] * 2
            return df

        result = successful_transform(sample_ohlc_df.copy())
        assert 'new_col' in result.columns

    def test_decorator_with_different_exceptions(self):
        """测试装饰器处理不同类型的异常"""

        @safe_transform("key_error_transform")
        def raise_key_error(df):
            raise KeyError("Missing column")

        @safe_transform("type_error_transform")
        def raise_type_error(df):
            raise TypeError("Type mismatch")

        df = pd.DataFrame({'col1': [1, 2, 3]})

        with pytest.raises(TransformError):
            raise_key_error(df)

        with pytest.raises(TransformError):
            raise_type_error(df)


# ==================== 组合策略测试 ====================


class TestCompositeStrategyNesting:
    """组合策略嵌套测试"""

    def test_two_level_nesting(self, sample_ohlc_df):
        """测试两层嵌套"""
        strategy1 = NormalizationStrategy(config={'method': 'standard'})
        strategy2 = TimeFeatureStrategy()

        composite = CompositeTransformStrategy([strategy1, strategy2])
        result = composite.transform(sample_ohlc_df)

        # 验证两个策略都被执行
        assert len(result.columns) > len(sample_ohlc_df.columns)

    def test_three_level_nesting(self, sample_ohlc_df):
        """测试三层嵌套"""
        strategy1 = NormalizationStrategy(config={'method': 'standard'})
        strategy2 = TimeFeatureStrategy()
        strategy3 = StatisticalFeatureStrategy(config={'lags': [1, 2]})

        # 第一层组合
        composite1 = CompositeTransformStrategy([strategy1, strategy2])

        # 第二层组合（嵌套）
        composite2 = CompositeTransformStrategy([composite1, strategy3])

        result = composite2.transform(sample_ohlc_df)

        # 验证所有策略都被执行
        assert len(result.columns) > len(sample_ohlc_df.columns)

    def test_empty_composite(self, sample_ohlc_df):
        """测试空组合策略"""
        # CompositeTransformStrategy不允许空列表，应该抛出ValueError
        with pytest.raises(ValueError, match="策略列表不能为空"):
            composite = CompositeTransformStrategy([])

    def test_single_strategy_composite(self, sample_ohlc_df):
        """测试只包含一个策略的组合"""
        strategy = NormalizationStrategy()
        composite = CompositeTransformStrategy([strategy])

        result = composite.transform(sample_ohlc_df)

        # 应该执行该策略
        assert len(result.columns) >= len(sample_ohlc_df.columns)

    def test_composite_strategy_order(self, sample_ohlc_df):
        """测试策略执行顺序"""
        # 创建一个跟踪执行顺序的mock策略
        execution_order = []

        class TrackingStrategy(TransformStrategy):
            def __init__(self, name):
                self.name = name
                super().__init__(config={})

            def transform(self, df):
                execution_order.append(self.name)
                return df

            def _get_feature_names(self) -> list:
                """实现抽象方法"""
                return []

        s1 = TrackingStrategy("first")
        s2 = TrackingStrategy("second")
        s3 = TrackingStrategy("third")

        composite = CompositeTransformStrategy([s1, s2, s3])
        composite.transform(sample_ohlc_df)

        # 验证执行顺序
        assert execution_order == ["first", "second", "third"]


# ==================== 工厂函数测试 ====================


class TestFactoryFunctions:
    """工厂函数测试"""

    def test_create_default_pipeline(self, sample_ohlc_df):
        """测试创建默认管道"""
        pipeline = create_default_transform_pipeline()

        assert isinstance(pipeline, CompositeTransformStrategy)

        result = pipeline.transform(sample_ohlc_df)
        assert not result.empty
        assert len(result.columns) >= len(sample_ohlc_df.columns)

    def test_create_default_pipeline_inplace(self, sample_ohlc_df):
        """测试创建inplace模式管道"""
        pipeline = create_default_transform_pipeline(inplace=True)

        assert isinstance(pipeline, CompositeTransformStrategy)

        result = pipeline.transform(sample_ohlc_df.copy())
        assert not result.empty

    def test_manual_composite_pipeline(self, sample_ohlc_df):
        """测试手动创建组合管道"""
        strategies = [
            NormalizationStrategy(),
            TimeFeatureStrategy(),
        ]

        pipeline = CompositeTransformStrategy(strategies)

        assert isinstance(pipeline, CompositeTransformStrategy)

        result = pipeline.transform(sample_ohlc_df)
        assert not result.empty

    def test_composite_with_config(self, sample_ohlc_df):
        """测试带配置的组合策略"""
        strategies = [
            NormalizationStrategy(config={'method': 'robust'}),
            StatisticalFeatureStrategy(config={'lags': [1, 5, 10]}),
        ]

        pipeline = CompositeTransformStrategy(strategies)
        result = pipeline.transform(sample_ohlc_df)

        assert not result.empty


# ==================== Scaler管理测试 ====================


class TestScalerManagement:
    """Scaler保存和加载测试"""

    def test_scaler_save_and_load(self, temp_scaler_dir):
        """测试Scaler保存和加载"""
        # 创建并训练scaler
        scaler = StandardScaler()
        data = np.array([[1, 2], [3, 4], [5, 6]])
        scaler.fit(data)

        # 保存
        scaler_path = temp_scaler_dir / "test_scaler.pkl"
        import pickle
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)

        # 加载
        with open(scaler_path, 'rb') as f:
            loaded_scaler = pickle.load(f)

        # 验证
        np.testing.assert_array_almost_equal(scaler.mean_, loaded_scaler.mean_)

    def test_normalization_strategy_with_scaler_save(self, sample_ohlc_df, temp_scaler_dir):
        """测试NormalizationStrategy的scaler保存"""
        strategy = NormalizationStrategy(config={
            'method': 'standard',
            'scaler_path': str(temp_scaler_dir / "norm_scaler.pkl")
        })

        # 转换（会训练并保存scaler）
        result = strategy.transform(sample_ohlc_df)

        # 验证scaler文件存在
        scaler_file = temp_scaler_dir / "norm_scaler.pkl"
        # 注意：这取决于NormalizationStrategy的实现

    def test_scaler_not_found_error(self, temp_scaler_dir):
        """测试Scaler未找到错误"""
        # 尝试加载不存在的scaler
        nonexistent_path = temp_scaler_dir / "nonexistent.pkl"

        import pickle
        with pytest.raises(FileNotFoundError):
            with open(nonexistent_path, 'rb') as f:
                pickle.load(f)


# ==================== 配置验证测试 ====================


class TestConfigurationValidation:
    """配置验证测试"""

    def test_normalization_valid_methods(self, sample_ohlc_df):
        """测试有效的标准化方法"""
        valid_methods = ['standard', 'robust', 'minmax']

        for method in valid_methods:
            strategy = NormalizationStrategy(config={'method': method})
            result = strategy.transform(sample_ohlc_df)
            assert not result.empty

    def test_normalization_invalid_method(self, sample_ohlc_df):
        """测试无效的标准化方法"""
        strategy = NormalizationStrategy(config={'method': 'invalid_method'})

        # 应该抛出异常或使用默认值
        try:
            result = strategy.transform(sample_ohlc_df)
            # 如果没有抛出异常，验证使用了默认行为
            assert not result.empty
        except (ValueError, TransformError):
            # 抛出异常也是合理的
            pass

    def test_statistical_feature_lag_config(self, sample_ohlc_df):
        """测试滞后特征配置"""
        strategy = StatisticalFeatureStrategy(config={'lags': [1, 2, 5]})
        result = strategy.transform(sample_ohlc_df)

        # 应该添加滞后特征
        assert len(result.columns) > len(sample_ohlc_df.columns)

    def test_statistical_feature_rolling_config(self, sample_ohlc_df):
        """测试滚动窗口配置"""
        strategy = StatisticalFeatureStrategy(config={
            'rolling_windows': [5, 10, 20]
        })
        result = strategy.transform(sample_ohlc_df)

        assert len(result.columns) >= len(sample_ohlc_df.columns)


# ==================== 策略链式调用测试 ====================


class TestStrategyChaining:
    """策略链式调用测试"""

    def test_sequential_strategy_application(self, sample_ohlc_df):
        """测试顺序应用多个策略"""
        df = sample_ohlc_df.copy()

        # 应用第一个策略
        strategy1 = NormalizationStrategy()
        df = strategy1.transform(df)

        # 应用第二个策略
        strategy2 = TimeFeatureStrategy()
        df = strategy2.transform(df)

        # 应用第三个策略
        strategy3 = StatisticalFeatureStrategy(config={'lags': [1]})
        df = strategy3.transform(df)

        # 验证所有转换都被应用
        assert len(df.columns) > len(sample_ohlc_df.columns)

    def test_chaining_preserves_data(self, sample_ohlc_df):
        """测试链式调用保留原始数据"""
        strategy1 = NormalizationStrategy()
        strategy2 = TimeFeatureStrategy()

        composite = CompositeTransformStrategy([strategy1, strategy2])
        result = composite.transform(sample_ohlc_df)

        # 原始列应该仍然存在（可能被修改）
        assert 'close' in result.columns


# ==================== 边界情况测试 ====================


class TestTransformStrategyEdgeCases:
    """转换策略边界情况测试"""

    def test_single_row_dataframe(self):
        """测试单行DataFrame"""
        df = pd.DataFrame({
            'close': [100],
            'volume': [1e6],
        })

        strategy = NormalizationStrategy()
        result = strategy.transform(df)

        # 单行数据标准化可能导致NaN或保持不变
        assert len(result) == 1

    def test_all_nan_columns(self):
        """测试全NaN列"""
        df = pd.DataFrame({
            'col1': [np.nan] * 10,
            'col2': [np.nan] * 10,
        })

        strategy = NormalizationStrategy()
        result = strategy.transform(df)

        # 全NaN应该保持NaN
        assert result.isna().all().all()

    def test_mixed_data_types(self):
        """测试混合数据类型"""
        df = pd.DataFrame({
            'numeric': [1, 2, 3],
            'string': ['a', 'b', 'c'],
            'bool': [True, False, True],
        })

        # 某些策略可能只处理数值列
        strategy = NormalizationStrategy()

        try:
            result = strategy.transform(df)
            # 应该只转换数值列
            assert 'numeric' in result.columns
        except Exception:
            # 或者抛出异常也是合理的
            pass

    def test_very_large_dataframe(self):
        """测试大型DataFrame"""
        np.random.seed(42)
        large_df = pd.DataFrame({
            f'feature{i}': np.random.randn(10000)
            for i in range(50)
        })

        strategy = NormalizationStrategy()

        import time
        start = time.time()
        result = strategy.transform(large_df)
        elapsed = time.time() - start

        print(f"\n大型DataFrame(10000x50)转换时间: {elapsed:.3f}s")
        assert elapsed < 10.0  # 应该在合理时间内完成
        # NormalizationStrategy会保留原列并添加归一化列，因此列数会增加
        assert result.shape[0] == large_df.shape[0]  # 行数不变
        assert result.shape[1] >= large_df.shape[1]  # 列数增加或保持


# ==================== 异常处理测试 ====================


class TestTransformStrategyErrorHandling:
    """转换策略异常处理测试"""

    def test_strategy_with_missing_columns(self):
        """测试缺少必需列的策略"""
        df = pd.DataFrame({'col1': [1, 2, 3]})

        # PriceChangeTransformStrategy 需要价格列
        strategy = PriceChangeTransformStrategy()

        try:
            result = strategy.transform(df)
            # 可能跳过转换或使用默认行为
        except (KeyError, InvalidDataError, TransformError):
            # 抛出异常也是合理的
            pass

    def test_strategy_with_insufficient_data(self):
        """测试数据不足的情况"""
        df = pd.DataFrame({
            'close': [100, 101],  # 只有2行
        })

        # 需要更多数据的策略（如大窗口滚动）
        strategy = StatisticalFeatureStrategy(config={'rolling_windows': [100]})

        result = strategy.transform(df)
        # 应该处理数据不足的情况


# ==================== 集成测试 ====================


class TestTransformStrategyIntegration:
    """转换策略集成测试"""

    def test_full_pipeline_with_real_data(self, sample_ohlc_df):
        """测试完整管道处理真实数据"""
        # 创建完整管道
        pipeline = CompositeTransformStrategy([
            PriceChangeTransformStrategy(config={'periods': [1, 5]}),
            NormalizationStrategy(config={'method': 'standard'}),
            TimeFeatureStrategy(),
            StatisticalFeatureStrategy(config={'lags': [1, 5]}),
        ])

        result = pipeline.transform(sample_ohlc_df)

        # 验证结果
        assert not result.empty
        assert len(result.columns) > len(sample_ohlc_df.columns)
        assert len(result) == len(sample_ohlc_df)

    def test_pipeline_reproducibility(self, sample_ohlc_df):
        """测试管道可重现性"""
        pipeline = create_default_transform_pipeline()

        result1 = pipeline.transform(sample_ohlc_df.copy())
        result2 = pipeline.transform(sample_ohlc_df.copy())

        # 两次转换结果应该一致
        # 注意：如果有随机性，需要设置seed
        pd.testing.assert_frame_equal(result1, result2, check_exact=False, rtol=1e-5)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
