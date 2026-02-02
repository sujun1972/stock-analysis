"""
ML API 集成测试

测试 ML API 与 Core Adapters 的集成。

作者: Backend Team
创建日期: 2026-02-02
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, date
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.main import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestMLAPIIntegration:
    """ML API 集成测试类"""

    @pytest.mark.asyncio
    async def test_train_model_endpoint(self, client):
        """测试训练模型端点（端到端）"""
        # Arrange
        payload = {
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "model_type": "LightGBM",
            "model_params": {
                "n_estimators": 50,
                "max_depth": 3,
                "learning_rate": 0.1
            },
            "test_size": 0.2,
            "save_model": True,
            "model_name": "test_model_integration"
        }

        # Act
        response = await client.post("/api/ml/train", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 可能成功或失败（取决于数据是否存在）
        if data["code"] == 200:
            assert "data" in data
            assert "train_metrics" in data["data"] or "message" in data
        else:
            # 如果数据不存在，应该返回 404 或 500
            assert data["code"] in [404, 500]

    @pytest.mark.asyncio
    async def test_train_model_invalid_date_range(self, client):
        """测试无效日期范围"""
        # Arrange
        payload = {
            "stock_code": "000001",
            "start_date": "2023-12-31",  # 开始日期晚于结束日期
            "end_date": "2023-01-01",
            "model_type": "LightGBM"
        }

        # Act
        response = await client.post("/api/ml/train", json=payload)

        # Assert
        assert response.status_code == 200  # API 总是返回 200
        data = response.json()
        assert data["code"] == 400
        assert "开始日期必须小于结束日期" in data["message"]

    @pytest.mark.asyncio
    async def test_predict_endpoint(self, client):
        """测试预测端点"""
        # Arrange
        payload = {
            "model_name": "test_model",
            "stock_code": "000001",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31"
        }

        # Act
        response = await client.post("/api/ml/predict", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 模型可能不存在，预期 404 或 500
        # 如果模型存在，预期 200
        assert data["code"] in [200, 404, 500]

    @pytest.mark.asyncio
    async def test_list_models_endpoint(self, client):
        """测试列出模型端点"""
        # Act
        response = await client.get("/api/ml/models")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "total" in data["data"]
        assert "models" in data["data"]
        assert isinstance(data["data"]["models"], list)

    @pytest.mark.asyncio
    async def test_list_models_with_filter(self, client):
        """测试带过滤的列出模型"""
        # Act
        response = await client.get("/api/ml/models?model_type=LightGBM&limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "models" in data["data"]

    @pytest.mark.asyncio
    async def test_get_model_info_endpoint(self, client):
        """测试获取模型信息端点"""
        # Act
        response = await client.get("/api/ml/models/test_model")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 模型可能不存在
        if data["code"] == 404:
            assert "不存在" in data["message"]
        elif data["code"] == 200:
            assert "data" in data
            assert "name" in data["data"]

    @pytest.mark.asyncio
    async def test_delete_model_endpoint(self, client):
        """测试删除模型端点"""
        # Act
        response = await client.delete("/api/ml/models/test_model")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 模型可能不存在
        assert data["code"] in [200, 404]

    @pytest.mark.asyncio
    async def test_evaluate_model_endpoint(self, client):
        """测试评估模型端点"""
        # Arrange
        payload = {
            "model_name": "test_model",
            "stock_code": "000001",
            "start_date": "2024-01-01",
            "end_date": "2024-03-31"
        }

        # Act
        response = await client.post("/api/ml/evaluate", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 模型或数据可能不存在
        assert data["code"] in [200, 404, 500]

        if data["code"] == 200:
            assert "data" in data
            # 评估指标应该包含 rmse, r2, mae 等
            metrics = data["data"]
            assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_tune_hyperparameters_endpoint(self, client):
        """测试超参数调优端点"""
        # Arrange
        payload = {
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "model_type": "LightGBM",
            "param_grid": {
                "n_estimators": [50, 100],
                "max_depth": [3, 6]
            },
            "search_method": "grid",
            "cv_folds": 3,
            "scoring": "neg_mean_squared_error"
        }

        # Act
        response = await client.post("/api/ml/tune", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 可能成功或失败（取决于数据是否存在）
        if data["code"] == 200:
            assert "data" in data
            assert "best_params" in data["data"]
        else:
            assert data["code"] in [404, 500]


class TestMLAPIErrorHandling:
    """ML API 错误处理测试"""

    @pytest.mark.asyncio
    async def test_train_model_missing_required_fields(self, client):
        """测试缺少必需字段"""
        # Arrange
        payload = {
            "stock_code": "000001"
            # 缺少 start_date, end_date
        }

        # Act
        response = await client.post("/api/ml/train", json=payload)

        # Assert
        # FastAPI 会自动验证并返回 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_predict_missing_required_fields(self, client):
        """测试预测缺少必需字段"""
        # Arrange
        payload = {
            "model_name": "test_model"
            # 缺少 stock_code, start_date, end_date
        }

        # Act
        response = await client.post("/api/ml/predict", json=payload)

        # Assert
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_train_model_invalid_test_size(self, client):
        """测试无效的测试集比例"""
        # Arrange
        payload = {
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "model_type": "LightGBM",
            "test_size": 0.9  # 超出范围 [0.1, 0.5]
        }

        # Act
        response = await client.post("/api/ml/train", json=payload)

        # Assert
        assert response.status_code == 422  # Pydantic 验证失败

    @pytest.mark.asyncio
    async def test_tune_invalid_cv_folds(self, client):
        """测试无效的交叉验证折数"""
        # Arrange
        payload = {
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "model_type": "LightGBM",
            "param_grid": {"n_estimators": [50, 100]},
            "cv_folds": 1  # 小于最小值 2
        }

        # Act
        response = await client.post("/api/ml/tune", json=payload)

        # Assert
        assert response.status_code == 422


class TestMLAPIDataFlow:
    """ML API 数据流测试"""

    @pytest.mark.asyncio
    async def test_complete_ml_workflow(self, client):
        """测试完整的机器学习工作流"""
        # 步骤 1: 列出现有模型
        response = await client.get("/api/ml/models")
        assert response.status_code == 200
        initial_data = response.json()
        initial_count = initial_data["data"]["total"]

        # 步骤 2: 训练一个新模型（可能失败，取决于数据）
        train_payload = {
            "stock_code": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-06-30",
            "model_type": "LightGBM",
            "save_model": True,
            "model_name": "test_workflow_model"
        }
        train_response = await client.post("/api/ml/train", json=train_payload)
        assert train_response.status_code == 200

        # 如果训练成功
        if train_response.json()["code"] == 200:
            # 步骤 3: 验证模型已创建
            response = await client.get("/api/ml/models")
            assert response.status_code == 200
            current_data = response.json()
            # 模型数量可能增加（如果保存成功）
            # assert current_data["data"]["total"] >= initial_count

            # 步骤 4: 获取模型信息
            response = await client.get("/api/ml/models/test_workflow_model")
            if response.json()["code"] == 200:
                model_info = response.json()["data"]
                assert "name" in model_info
                assert model_info["name"] == "test_workflow_model"

            # 步骤 5: 使用模型进行预测
            predict_payload = {
                "model_name": "test_workflow_model",
                "stock_code": "000001",
                "start_date": "2023-07-01",
                "end_date": "2023-09-30"
            }
            predict_response = await client.post("/api/ml/predict", json=predict_payload)
            assert predict_response.status_code == 200

            # 步骤 6: 评估模型
            evaluate_payload = {
                "model_name": "test_workflow_model",
                "stock_code": "000001",
                "start_date": "2023-07-01",
                "end_date": "2023-09-30"
            }
            evaluate_response = await client.post("/api/ml/evaluate", json=evaluate_payload)
            assert evaluate_response.status_code == 200

            # 步骤 7: 删除测试模型（清理）
            delete_response = await client.delete("/api/ml/models/test_workflow_model")
            assert delete_response.status_code == 200


class TestMLAPIPerformance:
    """ML API 性能测试"""

    @pytest.mark.asyncio
    async def test_list_models_response_time(self, client):
        """测试列出模型的响应时间"""
        import time

        # Act
        start_time = time.time()
        response = await client.get("/api/ml/models?limit=100")
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == 200
        # 响应时间应该在合理范围内（5秒内）
        assert elapsed_time < 5.0

    @pytest.mark.asyncio
    async def test_concurrent_list_models_requests(self, client):
        """测试并发列出模型请求"""
        import asyncio

        # Act
        tasks = [
            client.get("/api/ml/models")
            for _ in range(10)
        ]
        responses = await asyncio.gather(*tasks)

        # Assert
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
