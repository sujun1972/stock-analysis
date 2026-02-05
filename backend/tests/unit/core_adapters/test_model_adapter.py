"""
ModelAdapter 单元测试

测试机器学习模型适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-01
"""

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters.model_adapter import ModelAdapter


@pytest.fixture
def temp_model_dir():
    """创建临时模型目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # 清理
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def model_adapter(temp_model_dir):
    """创建模型适配器实例"""
    return ModelAdapter(model_dir=temp_model_dir)


@pytest.fixture
def sample_data():
    """创建示例训练数据"""
    np.random.seed(42)
    X_train = pd.DataFrame(np.random.randn(100, 10), columns=[f"feature_{i}" for i in range(10)])
    y_train = pd.Series(np.random.randn(100))
    X_test = pd.DataFrame(np.random.randn(30, 10), columns=[f"feature_{i}" for i in range(10)])
    y_test = pd.Series(np.random.randn(30))
    return X_train, y_train, X_test, y_test


@pytest.fixture
def mock_model():
    """创建模拟模型"""
    model = Mock()
    model.predict = Mock(return_value=np.random.randn(30))
    model.feature_importances_ = np.random.rand(10)
    return model


class TestModelAdapter:
    """ModelAdapter 单元测试类"""

    def test_init(self, model_adapter, temp_model_dir):
        """测试初始化"""
        assert model_adapter.model_dir == temp_model_dir
        assert temp_model_dir.exists()
        assert model_adapter.registry is not None

    @pytest.mark.asyncio
    async def test_predict(self, model_adapter, mock_model, sample_data):
        """测试模型预测"""
        # Arrange
        X_train, y_train, X_test, y_test = sample_data

        # Act
        predictions = await model_adapter.predict(mock_model, X_test)

        # Assert
        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == len(X_test)
        mock_model.predict.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_invalid_model(self, model_adapter, sample_data):
        """测试无效模型预测"""
        # Arrange
        X_train, y_train, X_test, y_test = sample_data
        invalid_model = Mock(spec=[])  # 没有 predict 方法

        # Act & Assert
        with pytest.raises(Exception):
            await model_adapter.predict(invalid_model, X_test)

    @pytest.mark.asyncio
    async def test_evaluate_model(self, model_adapter, mock_model, sample_data):
        """测试模型评估"""
        # Arrange
        X_train, y_train, X_test, y_test = sample_data

        # Mock ModelEvaluator
        with patch("app.core_adapters.model_adapter.ModelEvaluator") as MockEvaluator:
            mock_evaluator = MockEvaluator.return_value
            mock_evaluator.evaluate.return_value = {
                "mse": 0.5,
                "rmse": 0.707,
                "mae": 0.6,
                "r2": 0.8,
            }

            # Act
            result = await model_adapter.evaluate_model(mock_model, X_test, y_test)

            # Assert
            assert isinstance(result, dict)
            assert "mse" in result
            assert "rmse" in result
            assert result["r2"] == 0.8

    @pytest.mark.asyncio
    async def test_cross_validate(self, model_adapter, sample_data):
        """测试交叉验证"""
        # Arrange
        X_train, y_train, X_test, y_test = sample_data

        # Mock ModelTrainer
        with patch("app.core_adapters.model_adapter.ModelTrainer") as MockTrainer:
            mock_trainer = MockTrainer.return_value
            mock_trainer.train.return_value = Mock()
            mock_trainer.evaluate.return_value = {"rmse": 0.7}

            # Act
            result = await model_adapter.cross_validate(
                X_train, y_train, model_type="Ridge", n_folds=3
            )

            # Assert
            assert isinstance(result, dict)
            assert "mean_score" in result
            assert "std_score" in result
            assert "fold_scores" in result
            assert len(result["fold_scores"]) == 3

    def test_list_models_empty(self, model_adapter):
        """测试列出模型（空列表）"""
        # Mock registry
        model_adapter.registry.list_models = Mock(return_value=[])

        # Act
        import asyncio

        result = asyncio.run(model_adapter.list_models())

        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(self, model_adapter):
        """测试获取不存在的模型信息"""
        # Mock registry
        model_adapter.registry.get_model = Mock(return_value=None)

        # Act
        result = await model_adapter.get_model_info("non_existent_model")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_model(self, model_adapter):
        """测试删除模型"""
        # Mock registry
        model_adapter.registry.delete_model = Mock(return_value=True)

        # 添加模型到缓存
        model_adapter._loaded_models["test_model"] = Mock()

        # Act
        result = await model_adapter.delete_model("test_model")

        # Assert
        assert result is True
        assert "test_model" not in model_adapter._loaded_models


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
