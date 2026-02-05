"""
FeatureAdapter 单元测试

测试特征工程适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-01
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters.feature_adapter import FeatureAdapter


@pytest.fixture
def sample_df():
    """创建示例 DataFrame"""
    return pd.DataFrame({
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [102.0, 103.0, 104.0, 105.0, 106.0],
        'low': [99.0, 100.0, 101.0, 102.0, 103.0],
        'close': [101.0, 102.0, 103.0, 104.0, 105.0],
        'volume': [1000000, 1100000, 1200000, 1300000, 1400000]
    })


@pytest.fixture
def feature_adapter():
    """创建特征适配器实例"""
    return FeatureAdapter()


class TestFeatureAdapter:
    """FeatureAdapter 单元测试类"""

    @pytest.mark.asyncio
    async def test_add_technical_indicators_all(self, feature_adapter, sample_df):
        """测试添加所有技术指标"""
        # Act
        result = await feature_adapter.add_technical_indicators(sample_df)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)
        # 检查是否有新列添加
        assert len(result.columns) >= len(sample_df.columns)

    @pytest.mark.asyncio
    async def test_add_technical_indicators_specific(self, feature_adapter, sample_df):
        """测试添加特定技术指标"""
        # Act
        result = await feature_adapter.add_technical_indicators(
            sample_df,
            indicators=['ma', 'rsi']
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)

    @pytest.mark.asyncio
    async def test_add_alpha_factors_all(self, feature_adapter, sample_df):
        """测试添加所有 Alpha 因子"""
        # Act
        result = await feature_adapter.add_alpha_factors(sample_df)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)

    @pytest.mark.asyncio
    async def test_add_alpha_factors_specific(self, feature_adapter, sample_df):
        """测试添加特定 Alpha 因子"""
        # Act
        result = await feature_adapter.add_alpha_factors(
            sample_df,
            factors=['momentum', 'volatility']
        )

        # Assert
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_add_all_features(self, feature_adapter, sample_df):
        """测试添加所有特征"""
        # Act
        result = await feature_adapter.add_all_features(
            sample_df,
            include_indicators=True,
            include_factors=True,
            include_transforms=False
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)
        # 应该有技术指标和 Alpha 因子
        assert len(result.columns) > len(sample_df.columns)

    @pytest.mark.asyncio
    async def test_transform_features_standardize(self, feature_adapter, sample_df):
        """测试特征标准化"""
        # Act
        result = await feature_adapter.transform_features(
            sample_df,
            method="standardize",
            columns=['close', 'volume']
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_df)

    @pytest.mark.asyncio
    async def test_transform_features_normalize(self, feature_adapter, sample_df):
        """测试特征归一化"""
        # Act
        result = await feature_adapter.transform_features(
            sample_df,
            method="normalize"
        )

        # Assert
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_transform_features_log(self, feature_adapter, sample_df):
        """测试对数变换"""
        # Act
        result = await feature_adapter.transform_features(
            sample_df,
            method="log"
        )

        # Assert
        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_transform_features_invalid_method(self, feature_adapter, sample_df):
        """测试无效的转换方法"""
        # Act & Assert
        with pytest.raises(Exception):  # 应该抛出 FeatureEngineeringError
            await feature_adapter.transform_features(
                sample_df,
                method="invalid_method"
            )

    @pytest.mark.asyncio
    async def test_calculate_feature_importance(self, feature_adapter):
        """测试计算特征重要性"""
        # Arrange
        X = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100)
        })
        y = pd.Series(np.random.randn(100))

        # Act
        result = await feature_adapter.calculate_feature_importance(X, y)

        # Assert
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        assert all(isinstance(v, (int, float)) for v in result)

    @pytest.mark.asyncio
    async def test_select_features(self, feature_adapter):
        """测试特征选择"""
        # Arrange
        X = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100),
            'feature4': np.random.randn(100),
            'feature5': np.random.randn(100)
        })
        y = pd.Series(np.random.randn(100))

        # Act
        result = await feature_adapter.select_features(X, y, n_features=3)

        # Assert
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(f, str) for f in result)

    @pytest.mark.asyncio
    async def test_init_streaming_engine(self, feature_adapter):
        """测试初始化流式特征引擎"""
        # Act
        await feature_adapter.init_streaming_engine()

        # Assert
        assert feature_adapter.streaming_engine is not None

    @pytest.mark.asyncio
    async def test_update_streaming_features_without_init(self, feature_adapter):
        """测试未初始化时更新流式特征"""
        # Arrange
        new_data = {
            'open': 100.0,
            'high': 102.0,
            'low': 99.0,
            'close': 101.0,
            'volume': 1000000
        }

        # Act & Assert
        with pytest.raises(Exception):  # 应该抛出 FeatureEngineeringError
            await feature_adapter.update_streaming_features(new_data)

    @pytest.mark.asyncio
    async def test_get_feature_names(self, feature_adapter):
        """测试获取特征名称"""
        # Act
        result = await feature_adapter.get_feature_names()

        # Assert
        assert isinstance(result, dict)
        assert 'technical_indicators' in result
        assert 'alpha_factors' in result
        assert 'transforms' in result
        assert isinstance(result['technical_indicators'], list)
        assert isinstance(result['alpha_factors'], list)
        assert len(result['transforms']) == 4  # standardize, normalize, log, diff


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
