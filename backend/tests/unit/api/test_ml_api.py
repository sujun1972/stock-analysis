"""
ML API 单元测试

测试所有 ML API 端点的功能。

作者: Backend Team
创建日期: 2026-02-02
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.api.endpoints.ml import (
    train_model,
    predict,
    list_models,
    get_model_info,
    delete_model,
    evaluate_model,
    tune_hyperparameters,
    TrainModelRequest,
    PredictRequest,
    HyperparameterTuningRequest
)


@pytest.fixture
def mock_model_adapter():
    """创建模拟的 ModelAdapter"""
    with patch('app.api.endpoints.ml.model_adapter') as mock:
        yield mock


@pytest.fixture
def mock_data_adapter():
    """创建模拟的 DataAdapter"""
    with patch('app.api.endpoints.ml.data_adapter') as mock:
        yield mock


@pytest.fixture
def mock_feature_adapter():
    """创建模拟的 FeatureAdapter"""
    with patch('app.api.endpoints.ml.feature_adapter') as mock:
        yield mock


@pytest.fixture
def sample_train_request():
    """创建示例训练请求"""
    return TrainModelRequest(
        stock_code="000001",
        start_date="2022-01-01",
        end_date="2023-12-31",
        model_type="LightGBM",
        model_params={
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1
        },
        test_size=0.2,
        save_model=True,
        model_name="000001_lightgbm_v1"
    )


@pytest.fixture
def sample_df():
    """创建示例数据"""
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
    data = {
        'close': np.random.randn(len(dates)).cumsum() + 100,
        'open': np.random.randn(len(dates)).cumsum() + 100,
        'high': np.random.randn(len(dates)).cumsum() + 102,
        'low': np.random.randn(len(dates)).cumsum() + 98,
        'volume': np.random.randint(1000000, 10000000, len(dates)),
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def sample_df_with_features(sample_df):
    """创建带特征的示例数据"""
    df = sample_df.copy()
    # 添加一些模拟特征
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['rsi'] = np.random.uniform(30, 70, len(df))
    return df


class TestTrainModel:
    """测试训练模型端点"""

    @pytest.mark.asyncio
    async def test_train_model_success(
        self,
        sample_train_request,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试成功训练模型"""
        # Arrange
        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)

        training_result = {
            "model_name": "000001_lightgbm_v1",
            "model_path": "/path/to/model.pkl",
            "train_metrics": {
                "rmse": 0.05,
                "r2": 0.85,
                "mae": 0.03
            },
            "test_metrics": {
                "rmse": 0.06,
                "r2": 0.82,
                "mae": 0.04
            },
            "feature_importance": pd.Series({"ma_5": 0.3, "ma_20": 0.5}),
            "training_time": 15.5
        }
        mock_model_adapter.train_model = AsyncMock(return_value=training_result)

        # Act
        result = await train_model(sample_train_request)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "模型训练完成"
        assert result["data"]["model_name"] == "000001_lightgbm_v1"
        assert "train_metrics" in result["data"]
        assert "test_metrics" in result["data"]
        mock_data_adapter.get_daily_data.assert_called_once()
        mock_feature_adapter.add_all_features.assert_called_once()
        mock_model_adapter.train_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_train_model_invalid_date_range(self):
        """测试无效日期范围"""
        # Arrange
        invalid_request = TrainModelRequest(
            stock_code="000001",
            start_date="2023-12-31",  # 开始日期晚于结束日期
            end_date="2023-01-01",
            model_type="LightGBM"
        )

        # Act
        result = await train_model(invalid_request)

        # Assert
        assert result["code"] == 400
        assert "开始日期必须小于结束日期" in result["message"]

    @pytest.mark.asyncio
    async def test_train_model_no_data(
        self,
        sample_train_request,
        mock_data_adapter
    ):
        """测试无数据情况"""
        # Arrange
        mock_data_adapter.get_daily_data = AsyncMock(return_value=pd.DataFrame())

        # Act
        result = await train_model(sample_train_request)

        # Assert
        assert result["code"] == 404
        assert "无可用数据" in result["message"]

    @pytest.mark.asyncio
    async def test_train_model_insufficient_data(
        self,
        sample_train_request,
        mock_data_adapter,
        mock_feature_adapter
    ):
        """测试数据量不足"""
        # Arrange
        small_df = pd.DataFrame({
            'close': [10.0] * 50,
            'open': [10.0] * 50,
            'high': [10.5] * 50,
            'low': [9.5] * 50,
            'volume': [1000000] * 50
        })
        mock_data_adapter.get_daily_data = AsyncMock(return_value=small_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=small_df)

        # Act
        result = await train_model(sample_train_request)

        # Assert
        assert result["code"] == 400
        assert "数据量不足" in result["message"]

    @pytest.mark.asyncio
    async def test_train_model_adapter_error(
        self,
        sample_train_request,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试适配器执行错误"""
        # Arrange
        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)
        mock_model_adapter.train_model = AsyncMock(
            side_effect=Exception("训练失败")
        )

        # Act
        result = await train_model(sample_train_request)

        # Assert
        assert result["code"] == 500
        assert "模型训练失败" in result["message"]


class TestPredict:
    """测试预测端点"""

    @pytest.mark.asyncio
    async def test_predict_success(
        self,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试成功预测"""
        # Arrange
        request = PredictRequest(
            model_name="000001_lightgbm_v1",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        mock_model = Mock()
        mock_model_adapter.load_model = AsyncMock(return_value=mock_model)
        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)

        predictions = np.array([10.5, 10.8, 11.2])
        mock_model_adapter.predict = AsyncMock(return_value=predictions)

        # Act
        result = await predict(request)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "预测完成"
        assert "predictions" in result["data"]
        assert "dates" in result["data"]
        assert result["data"]["model_name"] == "000001_lightgbm_v1"
        assert result["data"]["stock_code"] == "000001"
        mock_model_adapter.load_model.assert_called_once_with("000001_lightgbm_v1")
        mock_model_adapter.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_model_not_found(self, mock_model_adapter):
        """测试模型不存在"""
        # Arrange
        request = PredictRequest(
            model_name="nonexistent_model",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        mock_model_adapter.load_model = AsyncMock(
            side_effect=FileNotFoundError("模型不存在")
        )

        # Act
        result = await predict(request)

        # Assert
        assert result["code"] == 500
        assert "预测失败" in result["message"]

    @pytest.mark.asyncio
    async def test_predict_no_data(self, mock_model_adapter, mock_data_adapter):
        """测试无数据"""
        # Arrange
        request = PredictRequest(
            model_name="000001_lightgbm_v1",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        mock_model = Mock()
        mock_model_adapter.load_model = AsyncMock(return_value=mock_model)
        mock_data_adapter.get_daily_data = AsyncMock(return_value=pd.DataFrame())

        # Act
        result = await predict(request)

        # Assert
        assert result["code"] == 404
        assert "无可用数据" in result["message"]


class TestListModels:
    """测试列出模型端点"""

    @pytest.mark.asyncio
    async def test_list_models_success(self, mock_model_adapter):
        """测试成功列出模型"""
        # Arrange
        models = [
            {
                "name": "000001_lightgbm_v1",
                "model_type": "LightGBM",
                "metrics": {"r2": 0.85},
                "created_at": "2024-01-01T12:00:00"
            },
            {
                "name": "000002_ridge_v1",
                "model_type": "Ridge",
                "metrics": {"r2": 0.75},
                "created_at": "2024-01-02T12:00:00"
            }
        ]
        mock_model_adapter.list_models = AsyncMock(return_value=models)

        # Act
        result = await list_models()

        # Assert
        assert result["code"] == 200
        assert result["message"] == "获取模型列表成功"
        assert result["data"]["total"] == 2
        assert len(result["data"]["models"]) == 2
        mock_model_adapter.list_models.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_models_with_filter(self, mock_model_adapter):
        """测试带过滤的列出模型"""
        # Arrange
        models = [
            {
                "name": "000001_lightgbm_v1",
                "model_type": "LightGBM",
                "metrics": {"r2": 0.85}
            }
        ]
        mock_model_adapter.list_models = AsyncMock(return_value=models)

        # Act
        result = await list_models(model_type="LightGBM", limit=10)

        # Assert
        assert result["code"] == 200
        assert result["data"]["total"] == 1
        mock_model_adapter.list_models.assert_called_once_with(
            model_type="LightGBM",
            limit=10
        )

    @pytest.mark.asyncio
    async def test_list_models_empty(self, mock_model_adapter):
        """测试空模型列表"""
        # Arrange
        mock_model_adapter.list_models = AsyncMock(return_value=[])

        # Act
        result = await list_models()

        # Assert
        assert result["code"] == 200
        assert result["data"]["total"] == 0
        assert result["data"]["models"] == []


class TestGetModelInfo:
    """测试获取模型信息端点"""

    @pytest.mark.asyncio
    async def test_get_model_info_success(self, mock_model_adapter):
        """测试成功获取模型信息"""
        # Arrange
        model_info = {
            "name": "000001_lightgbm_v1",
            "model_type": "LightGBM",
            "metrics": {"r2": 0.85, "rmse": 0.05},
            "params": {"n_estimators": 100},
            "created_at": "2024-01-01T12:00:00",
            "model_path": "/path/to/model.pkl"
        }
        mock_model_adapter.get_model_info = AsyncMock(return_value=model_info)

        # Act
        result = await get_model_info("000001_lightgbm_v1")

        # Assert
        assert result["code"] == 200
        assert result["message"] == "获取模型信息成功"
        assert result["data"]["name"] == "000001_lightgbm_v1"
        assert "metrics" in result["data"]
        mock_model_adapter.get_model_info.assert_called_once_with("000001_lightgbm_v1")

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self, mock_model_adapter):
        """测试模型不存在"""
        # Arrange
        mock_model_adapter.get_model_info = AsyncMock(return_value=None)

        # Act
        result = await get_model_info("nonexistent_model")

        # Assert
        assert result["code"] == 404
        assert "不存在" in result["message"]


class TestDeleteModel:
    """测试删除模型端点"""

    @pytest.mark.asyncio
    async def test_delete_model_success(self, mock_model_adapter):
        """测试成功删除模型"""
        # Arrange
        mock_model_adapter.delete_model = AsyncMock(return_value=True)

        # Act
        result = await delete_model("000001_lightgbm_v1")

        # Assert
        assert result["code"] == 200
        assert result["message"] == "模型删除成功"
        assert result["data"]["model_name"] == "000001_lightgbm_v1"
        assert result["data"]["deleted"] is True
        mock_model_adapter.delete_model.assert_called_once_with("000001_lightgbm_v1")

    @pytest.mark.asyncio
    async def test_delete_model_not_found(self, mock_model_adapter):
        """测试删除不存在的模型"""
        # Arrange
        mock_model_adapter.delete_model = AsyncMock(return_value=False)

        # Act
        result = await delete_model("nonexistent_model")

        # Assert
        assert result["code"] == 404
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_model_error(self, mock_model_adapter):
        """测试删除模型错误"""
        # Arrange
        mock_model_adapter.delete_model = AsyncMock(
            side_effect=Exception("删除失败")
        )

        # Act
        result = await delete_model("000001_lightgbm_v1")

        # Assert
        assert result["code"] == 500
        assert "删除模型失败" in result["message"]


class TestEvaluateModel:
    """测试评估模型端点"""

    @pytest.mark.asyncio
    async def test_evaluate_model_success(
        self,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试成功评估模型"""
        # Arrange
        mock_model = Mock()
        mock_model_adapter.load_model = AsyncMock(return_value=mock_model)
        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)

        metrics = {
            "rmse": 0.06,
            "r2": 0.82,
            "mae": 0.04,
            "mape": 5.2
        }
        mock_model_adapter.evaluate_model = AsyncMock(return_value=metrics)

        # Act
        result = await evaluate_model(
            model_name="000001_lightgbm_v1",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        # Assert
        assert result["code"] == 200
        assert result["message"] == "模型评估完成"
        assert result["data"]["rmse"] == 0.06
        assert result["data"]["r2"] == 0.82
        mock_model_adapter.evaluate_model.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_model_no_data(self, mock_model_adapter, mock_data_adapter):
        """测试无数据"""
        # Arrange
        mock_model = Mock()
        mock_model_adapter.load_model = AsyncMock(return_value=mock_model)
        mock_data_adapter.get_daily_data = AsyncMock(return_value=pd.DataFrame())

        # Act
        result = await evaluate_model(
            model_name="000001_lightgbm_v1",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        # Assert
        assert result["code"] == 404
        assert "无可用数据" in result["message"]


class TestTuneHyperparameters:
    """测试超参数调优端点"""

    @pytest.mark.asyncio
    async def test_tune_hyperparameters_success(
        self,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试成功调优超参数"""
        # Arrange
        request = HyperparameterTuningRequest(
            stock_code="000001",
            start_date="2022-01-01",
            end_date="2023-12-31",
            model_type="LightGBM",
            param_grid={
                "n_estimators": [50, 100, 200],
                "max_depth": [3, 6, 9],
                "learning_rate": [0.01, 0.05, 0.1]
            },
            search_method="grid",
            cv_folds=5,
            scoring="neg_mean_squared_error"
        )

        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)

        tuning_result = {
            "best_params": {
                "n_estimators": 100,
                "max_depth": 6,
                "learning_rate": 0.1
            },
            "best_score": -0.0036,
            "cv_results": {
                "mean_test_score": [-0.0036, -0.0040, -0.0045],
                "std_test_score": [0.0005, 0.0007, 0.0008]
            }
        }
        mock_model_adapter.tune_hyperparameters = AsyncMock(return_value=tuning_result)

        # Act
        result = await tune_hyperparameters(request)

        # Assert
        assert result["code"] == 200
        assert result["message"] == "超参数调优完成"
        assert "best_params" in result["data"]
        assert result["data"]["best_params"]["n_estimators"] == 100
        mock_model_adapter.tune_hyperparameters.assert_called_once()

    @pytest.mark.asyncio
    async def test_tune_hyperparameters_no_data(
        self,
        mock_data_adapter
    ):
        """测试无数据"""
        # Arrange
        request = HyperparameterTuningRequest(
            stock_code="000001",
            start_date="2022-01-01",
            end_date="2023-12-31",
            model_type="LightGBM",
            param_grid={"n_estimators": [50, 100]}
        )

        mock_data_adapter.get_daily_data = AsyncMock(return_value=pd.DataFrame())

        # Act
        result = await tune_hyperparameters(request)

        # Assert
        assert result["code"] == 404
        assert "无可用数据" in result["message"]

    @pytest.mark.asyncio
    async def test_tune_hyperparameters_error(
        self,
        mock_model_adapter,
        mock_data_adapter,
        mock_feature_adapter,
        sample_df,
        sample_df_with_features
    ):
        """测试调优错误"""
        # Arrange
        request = HyperparameterTuningRequest(
            stock_code="000001",
            start_date="2022-01-01",
            end_date="2023-12-31",
            model_type="LightGBM",
            param_grid={"n_estimators": [50, 100]}
        )

        mock_data_adapter.get_daily_data = AsyncMock(return_value=sample_df)
        mock_feature_adapter.add_all_features = AsyncMock(return_value=sample_df_with_features)
        mock_model_adapter.tune_hyperparameters = AsyncMock(
            side_effect=Exception("调优失败")
        )

        # Act
        result = await tune_hyperparameters(request)

        # Assert
        assert result["code"] == 500
        assert "超参数调优失败" in result["message"]


class TestRequestValidation:
    """测试请求模型验证"""

    def test_train_model_request_valid(self):
        """测试有效的训练请求"""
        # Act
        request = TrainModelRequest(
            stock_code="000001",
            start_date="2022-01-01",
            end_date="2023-12-31",
            model_type="LightGBM"
        )

        # Assert
        assert request.stock_code == "000001"
        assert request.model_type == "LightGBM"
        assert request.test_size == 0.2  # 默认值

    def test_train_model_request_invalid_test_size(self):
        """测试无效的测试集比例"""
        with pytest.raises(Exception):  # Pydantic ValidationError
            TrainModelRequest(
                stock_code="000001",
                start_date="2022-01-01",
                end_date="2023-12-31",
                model_type="LightGBM",
                test_size=0.8  # 超出范围 [0.1, 0.5]
            )

    def test_predict_request_valid(self):
        """测试有效的预测请求"""
        # Act
        request = PredictRequest(
            model_name="000001_lightgbm_v1",
            stock_code="000001",
            start_date="2024-01-01",
            end_date="2024-03-31"
        )

        # Assert
        assert request.model_name == "000001_lightgbm_v1"
        assert request.stock_code == "000001"

    def test_hyperparameter_tuning_request_valid(self):
        """测试有效的超参数调优请求"""
        # Act
        request = HyperparameterTuningRequest(
            stock_code="000001",
            start_date="2022-01-01",
            end_date="2023-12-31",
            model_type="LightGBM",
            param_grid={"n_estimators": [50, 100]}
        )

        # Assert
        assert request.stock_code == "000001"
        assert request.cv_folds == 5  # 默认值
        assert request.search_method == "grid"  # 默认值


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
