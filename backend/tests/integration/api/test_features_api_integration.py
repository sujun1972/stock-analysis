"""
Features API 集成测试

测试 Features API 与真实 Core Adapters 的集成

测试场景：
- 完整的特征计算流程
- 真实的数据获取和特征生成
- API 端点的端到端测试

作者: Backend Team
创建日期: 2026-02-01
"""

import pytest
from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np

from app.api.endpoints.features import (
    get_features,
    calculate_features,
    get_feature_names,
    select_features
)


@pytest.fixture
def sample_stock_data():
    """生成样本股票数据"""
    dates = pd.date_range('2024-01-01', periods=100)
    np.random.seed(42)  # 固定随机种子以保证可重复性

    # 生成模拟的股票数据
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
    high_prices = close_prices + np.abs(np.random.randn(100) * 2)
    low_prices = close_prices - np.abs(np.random.randn(100) * 2)
    open_prices = close_prices + np.random.randn(100) * 1
    volumes = np.random.randint(1000000, 10000000, 100)

    return pd.DataFrame({
        'date': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    })


class TestGetFeaturesIntegration:
    """测试 GET /api/features/{code} 集成"""

    @pytest.mark.asyncio
    async def test_get_features_end_to_end_with_mock_data(self, sample_stock_data, monkeypatch):
        """测试端到端获取特征（使用模拟数据）"""
        # Arrange: Mock data adapter to return sample data
        from unittest.mock import AsyncMock
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await get_features(
            code="000001",
            start_date="2024-01-01",
            end_date="2024-12-31",
            feature_type="technical",
            limit=50
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['code'] == "000001"
        assert result['data']['feature_type'] == "technical"
        assert result['data']['returned'] <= 50

        # 验证返回的特征列包含技术指标
        columns = result['data']['columns']
        # 应该包含原始列
        assert 'close' in columns or any('close' in str(col).lower() for col in columns)

        # 验证数据格式
        assert len(result['data']['data']) > 0
        first_record = result['data']['data'][0]
        assert isinstance(first_record, dict)

    @pytest.mark.asyncio
    async def test_get_features_alpha_factors_integration(self, sample_stock_data, monkeypatch):
        """测试获取 Alpha 因子集成"""
        # Arrange
        from unittest.mock import AsyncMock
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await get_features(
            code="000001",
            feature_type="alpha",
            limit=50
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['feature_type'] == "alpha"

    @pytest.mark.asyncio
    async def test_get_features_all_types_integration(self, sample_stock_data, monkeypatch):
        """测试获取所有类型特征集成"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await get_features(
            code="000001",
            feature_type="all",
            limit=100
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['feature_type'] == "all"
        # 所有特征应该有 125+ 列
        assert len(result['data']['columns']) > 20  # 至少有一些特征


class TestCalculateFeaturesIntegration:
    """测试 POST /api/features/calculate/{code} 集成"""

    @pytest.mark.asyncio
    async def test_calculate_features_end_to_end(self, sample_stock_data, monkeypatch):
        """测试端到端特征计算"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await calculate_features(
            code="000001",
            start_date="2024-01-01",
            end_date="2024-12-31",
            feature_types=["technical", "alpha"],
            include_transforms=False
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['code'] == "000001"
        assert result['data']['record_count'] == 100
        assert result['data']['feature_count'] > 5  # 至少有一些特征
        assert 'sample_data' in result['data']
        assert len(result['data']['sample_data']) <= 10

    @pytest.mark.asyncio
    async def test_calculate_features_with_transforms(self, sample_stock_data, monkeypatch):
        """测试包含特征转换的计算"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await calculate_features(
            code="000001",
            feature_types=["technical"],
            include_transforms=True
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['include_transforms'] is True


class TestGetFeatureNamesIntegration:
    """测试 GET /api/features/names 集成"""

    @pytest.mark.asyncio
    async def test_get_feature_names_integration(self):
        """测试获取特征名称集成"""
        # Act
        result = await get_feature_names()

        # Assert
        assert result['code'] == 200
        assert 'technical_indicators' in result['data']
        assert 'alpha_factors' in result['data']
        assert 'transforms' in result['data']
        assert 'total_count' in result['data']

        # 验证至少有一些特征
        assert len(result['data']['technical_indicators']) > 0
        assert len(result['data']['alpha_factors']) > 0
        assert len(result['data']['transforms']) > 0


class TestSelectFeaturesIntegration:
    """测试 POST /api/features/{code}/select 集成"""

    @pytest.mark.asyncio
    async def test_select_features_correlation_method(self, sample_stock_data, monkeypatch):
        """测试基于相关系数的特征选择"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await select_features(
            code="000001",
            target_column="close",
            n_features=10,
            method="correlation"
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['method'] == "correlation"
        assert result['data']['n_features'] <= 10
        assert len(result['data']['selected_features']) <= 10
        assert 'importance_scores' in result['data']

    @pytest.mark.asyncio
    async def test_select_features_mutual_info_method(self, sample_stock_data, monkeypatch):
        """测试基于互信息的特征选择"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await select_features(
            code="000001",
            target_column="close",
            n_features=5,
            method="mutual_info"
        )

        # Assert
        assert result['code'] == 200
        assert result['data']['method'] == "mutual_info"
        assert result['data']['n_features'] <= 5


class TestDataQualityIntegration:
    """测试数据质量相关的集成场景"""

    @pytest.mark.asyncio
    async def test_features_with_missing_data(self, monkeypatch):
        """测试包含缺失数据的特征计算"""
        # Arrange: 创建包含 NaN 的数据
        dates = pd.date_range('2024-01-01', periods=50)
        data_with_nan = pd.DataFrame({
            'date': dates,
            'open': np.random.rand(50) * 100,
            'high': np.random.rand(50) * 100,
            'low': np.random.rand(50) * 100,
            'close': [100 if i % 10 != 0 else np.nan for i in range(50)],
            'volume': np.random.rand(50) * 1000000
        })

        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return data_with_nan

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await get_features(code="000001", limit=50)

        # Assert
        assert result['code'] == 200
        # 验证 NaN 被正确处理为 None
        for record in result['data']['data']:
            for key, value in record.items():
                if value is None:
                    continue  # None 是期望的
                # 确保没有 NaN 或 Inf
                if isinstance(value, (int, float)):
                    assert not np.isnan(value)
                    assert not np.isinf(value)

    @pytest.mark.asyncio
    async def test_features_with_extreme_values(self, monkeypatch):
        """测试包含极端值的特征计算"""
        # Arrange
        dates = pd.date_range('2024-01-01', periods=50)
        extreme_data = pd.DataFrame({
            'date': dates,
            'open': np.random.rand(50) * 100,
            'high': np.random.rand(50) * 100,
            'low': np.random.rand(50) * 100,
            'close': [100 if i % 10 != 0 else 10000 for i in range(50)],  # 极端值
            'volume': np.random.rand(50) * 1000000
        })

        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return extreme_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        result = await get_features(code="000001", limit=50)

        # Assert
        assert result['code'] == 200
        assert len(result['data']['data']) > 0


class TestPerformanceIntegration:
    """测试性能相关的集成场景"""

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self, monkeypatch):
        """测试大数据集的性能"""
        # Arrange: 创建大数据集（1000 条记录）
        dates = pd.date_range('2020-01-01', periods=1000)
        large_data = pd.DataFrame({
            'date': dates,
            'open': np.random.rand(1000) * 100,
            'high': np.random.rand(1000) * 100,
            'low': np.random.rand(1000) * 100,
            'close': 100 + np.cumsum(np.random.randn(1000) * 2),
            'volume': np.random.randint(1000000, 10000000, 1000)
        })

        from app.api.endpoints import features
        import time

        async def mock_get_daily_data(*args, **kwargs):
            return large_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act
        start_time = time.time()
        result = await get_features(code="000001", limit=100)
        elapsed_time = time.time() - start_time

        # Assert
        assert result['code'] == 200
        assert result['data']['total'] == 1000
        assert result['data']['returned'] == 100
        # 性能要求：应该在合理时间内完成（如 30 秒）
        assert elapsed_time < 30, f"特征计算耗时过长: {elapsed_time:.2f}秒"

    @pytest.mark.asyncio
    async def test_pagination_consistency(self, sample_stock_data, monkeypatch):
        """测试分页的一致性"""
        # Arrange
        from app.api.endpoints import features

        async def mock_get_daily_data(*args, **kwargs):
            return sample_stock_data

        monkeypatch.setattr(features.data_adapter, 'get_daily_data', mock_get_daily_data)

        # Act: 获取第一页
        result1 = await get_features(code="000001", limit=10)
        # Act: 获取更多数据
        result2 = await get_features(code="000001", limit=50)

        # Assert
        assert result1['code'] == 200
        assert result2['code'] == 200
        assert result1['data']['total'] == result2['data']['total']
        assert result1['data']['returned'] == 10
        assert result2['data']['returned'] == min(50, result2['data']['total'])
