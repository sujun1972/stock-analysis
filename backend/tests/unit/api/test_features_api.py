"""
Features API 单元测试

测试 Features API 端点的所有功能（使用 Mock）

测试覆盖：
- GET /api/features/{code} - 获取特征数据
- POST /api/features/calculate/{code} - 计算特征
- GET /api/features/names - 获取特征名称
- POST /api/features/{code}/select - 特征选择

作者: Backend Team
创建日期: 2026-02-01
"""

from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from app.api.endpoints.features import (
    calculate_features,
    get_feature_names,
    get_features,
    select_features,
)


class TestGetFeatures:
    """测试 GET /api/features/{code} 端点"""

    @pytest.mark.asyncio
    async def test_get_features_success_all_types(self):
        """测试获取所有类型特征 - 成功"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "open": np.random.rand(100) * 100,
                "high": np.random.rand(100) * 100,
                "low": np.random.rand(100) * 100,
                "close": np.random.rand(100) * 100,
                "volume": np.random.rand(100) * 1000000,
            }
        )

        mock_df_with_features = mock_df.copy()
        mock_df_with_features["ma_5"] = mock_df["close"].rolling(5).mean()
        mock_df_with_features["rsi_14"] = np.random.rand(100) * 100

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df_with_features)

            # Act
            result = await get_features(
                code="000001",
                start_date="2024-01-01",
                end_date="2024-12-31",
                feature_type="all",
                limit=50,
            )

            # Assert
            assert result["code"] == 200
            assert result["message"] == "获取特征数据成功"
            assert result["data"]["code"] == "000001"
            assert result["data"]["feature_type"] == "all"
            assert result["data"]["returned"] <= 50
            assert "columns" in result["data"]
            assert "data" in result["data"]

            # 验证调用
            mock_data.get_daily_data.assert_called_once()
            mock_feature.add_all_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_features_technical_indicators_only(self):
        """测试仅获取技术指标"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=50),
                "close": np.random.rand(50) * 100,
                "volume": np.random.rand(50) * 1000000,
            }
        )

        mock_df_with_indicators = mock_df.copy()
        mock_df_with_indicators["ma_5"] = mock_df["close"].rolling(5).mean()

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_technical_indicators = AsyncMock(return_value=mock_df_with_indicators)

            # Act
            result = await get_features(code="000001", feature_type="technical", limit=50)

            # Assert
            assert result["code"] == 200
            assert result["data"]["feature_type"] == "technical"
            mock_feature.add_technical_indicators.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_features_alpha_factors_only(self):
        """测试仅获取 Alpha 因子"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=50),
                "close": np.random.rand(50) * 100,
                "volume": np.random.rand(50) * 1000000,
            }
        )

        mock_df_with_factors = mock_df.copy()
        mock_df_with_factors["momentum_5d"] = np.random.rand(50)

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_alpha_factors = AsyncMock(return_value=mock_df_with_factors)

            # Act
            result = await get_features(code="000001", feature_type="alpha", limit=50)

            # Assert
            assert result["code"] == 200
            assert result["data"]["feature_type"] == "alpha"
            mock_feature.add_alpha_factors.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_features_stock_not_found(self):
        """测试股票不存在"""
        # Arrange
        with patch("app.api.endpoints.features.data_adapter") as mock_data:
            mock_data.get_daily_data = AsyncMock(return_value=pd.DataFrame())

            # Act
            result = await get_features(code="999999")

            # Assert
            assert result["code"] == 404
            assert "无日线数据" in result["message"]

    @pytest.mark.asyncio
    async def test_get_features_invalid_date_format(self):
        """测试日期格式错误"""
        # Arrange
        with patch("app.api.endpoints.features.data_adapter") as mock_data:
            mock_data.get_daily_data = AsyncMock(return_value=pd.DataFrame())

            # Act
            result = await get_features(code="000001", start_date="invalid-date")

            # Assert
            assert result["code"] == 400
            assert "日期格式错误" in result["message"]

    @pytest.mark.asyncio
    async def test_get_features_with_limit(self):
        """测试限制返回记录数"""
        # Arrange
        mock_df = pd.DataFrame(
            {"date": pd.date_range("2024-01-01", periods=1000), "close": np.random.rand(1000) * 100}
        )

        mock_df_with_features = mock_df.copy()
        mock_df_with_features["ma_5"] = mock_df["close"].rolling(5).mean()

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df_with_features)

            # Act
            result = await get_features(code="000001", limit=100)

            # Assert
            assert result["code"] == 200
            assert result["data"]["returned"] == 100
            assert result["data"]["total"] == 1000
            assert result["data"]["has_more"] is True


class TestCalculateFeatures:
    """测试 POST /api/features/calculate/{code} 端点"""

    @pytest.mark.asyncio
    async def test_calculate_features_success(self):
        """测试特征计算 - 成功"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "open": np.random.rand(100) * 100,
                "high": np.random.rand(100) * 100,
                "low": np.random.rand(100) * 100,
                "close": np.random.rand(100) * 100,
                "volume": np.random.rand(100) * 1000000,
            }
        )

        mock_df_with_features = mock_df.copy()
        for i in range(50):  # 模拟 50+ 特征
            mock_df_with_features[f"feature_{i}"] = np.random.rand(100)

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df_with_features)

            # Act
            result = await calculate_features(
                code="000001",
                start_date="2024-01-01",
                end_date="2024-12-31",
                feature_types=["technical", "alpha"],
                include_transforms=False,
            )

            # Assert
            assert result["code"] == 200
            assert result["message"] == "特征计算成功"
            assert result["data"]["code"] == "000001"
            assert result["data"]["record_count"] == 100
            assert result["data"]["feature_count"] > 50
            assert "columns" in result["data"]
            assert "sample_data" in result["data"]
            assert len(result["data"]["sample_data"]) <= 10

    @pytest.mark.asyncio
    async def test_calculate_features_with_transforms(self):
        """测试包含特征转换的计算"""
        # Arrange
        mock_df = pd.DataFrame(
            {"date": pd.date_range("2024-01-01", periods=50), "close": np.random.rand(50) * 100}
        )

        mock_df_with_features = mock_df.copy()
        mock_df_with_features["ma_5"] = np.random.rand(50)

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df_with_features)

            # Act
            result = await calculate_features(
                code="000001", feature_types=["technical"], include_transforms=True
            )

            # Assert
            assert result["code"] == 200
            assert result["data"]["include_transforms"] is True
            mock_feature.add_all_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_features_stock_not_found(self):
        """测试计算特征 - 股票不存在"""
        # Arrange
        with patch("app.api.endpoints.features.data_adapter") as mock_data:
            mock_data.get_daily_data = AsyncMock(return_value=pd.DataFrame())

            # Act
            result = await calculate_features(code="999999")

            # Assert
            assert result["code"] == 404
            assert "无日线数据" in result["message"]


class TestGetFeatureNames:
    """测试 GET /api/features/names 端点"""

    @pytest.mark.asyncio
    async def test_get_feature_names_success(self):
        """测试获取特征名称 - 成功"""
        # Arrange
        mock_names = {
            "technical_indicators": ["ma", "ema", "macd", "rsi", "kdj"],
            "alpha_factors": ["momentum", "reversal", "volatility"],
            "transforms": ["standardize", "normalize", "log", "diff"],
        }

        with patch("app.api.endpoints.features.feature_adapter") as mock_feature:
            mock_feature.get_feature_names = AsyncMock(return_value=mock_names)

            # Act
            result = await get_feature_names()

            # Assert
            assert result["code"] == 200
            assert result["message"] == "获取特征名称成功"
            assert "technical_indicators" in result["data"]
            assert "alpha_factors" in result["data"]
            assert "transforms" in result["data"]
            assert "total_count" in result["data"]
            assert result["data"]["total_count"]["technical_indicators"] == 5
            assert result["data"]["total_count"]["alpha_factors"] == 3
            assert result["data"]["total_count"]["transforms"] == 4


class TestSelectFeatures:
    """测试 POST /api/features/{code}/select 端点"""

    @pytest.mark.asyncio
    async def test_select_features_success(self):
        """测试特征选择 - 成功"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "close": np.random.rand(100) * 100,
                "ma_5": np.random.rand(100) * 100,
                "ma_10": np.random.rand(100) * 100,
                "rsi_14": np.random.rand(100) * 100,
                "macd": np.random.rand(100),
            }
        )

        mock_selected_features = ["ma_5", "rsi_14", "macd"]
        mock_importance = pd.Series({"ma_5": 0.85, "rsi_14": 0.78, "macd": 0.65})

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df)
            mock_feature.select_features = AsyncMock(return_value=mock_selected_features)
            mock_feature.calculate_feature_importance = AsyncMock(return_value=mock_importance)

            # Act
            result = await select_features(
                code="000001", target_column="close", n_features=3, method="correlation"
            )

            # Assert
            assert result["code"] == 200
            assert result["message"] == "特征选择成功"
            assert result["data"]["code"] == "000001"
            assert result["data"]["method"] == "correlation"
            assert result["data"]["n_features"] == 3
            assert len(result["data"]["selected_features"]) == 3
            assert "importance_scores" in result["data"]

    @pytest.mark.asyncio
    async def test_select_features_invalid_target_column(self):
        """测试特征选择 - 目标列不存在"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "close": np.random.rand(100) * 100,
                "ma_5": np.random.rand(100) * 100,
            }
        )

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df)

            # Act
            result = await select_features(
                code="000001", target_column="invalid_column", n_features=3
            )

            # Assert
            assert result["code"] == 400
            assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_select_features_mutual_info_method(self):
        """测试特征选择 - 使用互信息方法"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "close": np.random.rand(100) * 100,
                "ma_5": np.random.rand(100) * 100,
                "rsi_14": np.random.rand(100) * 100,
            }
        )

        mock_selected_features = ["ma_5", "rsi_14"]
        mock_importance = pd.Series({"ma_5": 0.92, "rsi_14": 0.88})

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df)
            mock_feature.select_features = AsyncMock(return_value=mock_selected_features)
            mock_feature.calculate_feature_importance = AsyncMock(return_value=mock_importance)

            # Act
            result = await select_features(code="000001", method="mutual_info", n_features=2)

            # Assert
            assert result["code"] == 200
            assert result["data"]["method"] == "mutual_info"


class TestEdgeCases:
    """测试边界情况和异常处理"""

    @pytest.mark.asyncio
    async def test_get_features_with_nan_and_inf(self):
        """测试处理 NaN 和 Inf 值"""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "close": [100, np.nan, 102, np.inf, 104, -np.inf, 106, 107, np.nan, 109],
                "ma_5": [100, 101, np.inf, 103, 104, 105, -np.inf, 107, 108, np.nan],
            }
        )

        with (
            patch("app.api.endpoints.features.data_adapter") as mock_data,
            patch("app.api.endpoints.features.feature_adapter") as mock_feature,
        ):

            mock_data.get_daily_data = AsyncMock(return_value=mock_df)
            mock_feature.add_all_features = AsyncMock(return_value=mock_df)

            # Act
            result = await get_features(code="000001")

            # Assert
            assert result["code"] == 200
            # 验证返回的数据中没有 Inf 值
            for record in result["data"]["data"]:
                for value in record.values():
                    if value is not None:
                        assert value != np.inf
                        assert value != -np.inf

    @pytest.mark.asyncio
    async def test_calculate_features_empty_date_range(self):
        """测试空的日期范围"""
        # Arrange
        with patch("app.api.endpoints.features.data_adapter") as mock_data:
            mock_data.get_daily_data = AsyncMock(return_value=pd.DataFrame())

            # Act
            result = await calculate_features(
                code="000001", start_date="2025-01-01", end_date="2025-01-02"
            )

            # Assert
            assert result["code"] == 404

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="TestClient不完全支持FastAPI全局异常处理器，需要集成测试环境")
    async def test_get_features_internal_error(self):
        """测试内部错误处理"""
        # Arrange
        with patch("app.api.endpoints.features.data_adapter") as mock_data:
            mock_data.get_daily_data = AsyncMock(side_effect=Exception("数据库连接失败"))

            # Act
            result = await get_features(code="000001")

            # Assert
            assert result["code"] == 500
            assert "失败" in result["message"]
