"""
ML API 集成测试

测试 ml.py 中的所有端点：
- POST /api/ml/train - 创建训练任务
- GET /api/ml/tasks/{task_id} - 获取任务状态
- GET /api/ml/tasks - 列出训练任务
- DELETE /api/ml/tasks/{task_id} - 删除任务
- GET /api/ml/tasks/{task_id}/stream - 流式推送训练进度
- POST /api/ml/predict - 模型预测
- GET /api/ml/models - 列出可用模型
- GET /api/ml/features/available - 获取可用特征列表
- GET /api/ml/features/snapshot - 获取特征快照

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.api.endpoints.ml import (
    create_training_task,
    delete_task,
    get_available_features,
    get_feature_snapshot,
    get_task_status,
    list_models,
    list_tasks,
    predict,
    stream_task_progress,
)
from app.models.ml_models import MLPredictionRequest, MLTrainingTaskCreate


class TestCreateTrainingTask:
    """测试 POST /api/ml/train 端点"""

    @pytest.mark.asyncio
    async def test_create_training_task_success(self):
        """测试成功创建训练任务"""
        # Arrange
        request_data = MLTrainingTaskCreate(
            symbol="000001",
            start_date="2023-01-01",
            end_date="2023-12-31",
            model_type="lightgbm",
            target_period=5,
        )

        mock_task_id = "task_123456"
        mock_task = {
            "task_id": mock_task_id,
            "status": "pending",
            "created_at": datetime.now(),
            "config": request_data.dict(),
            "progress": 0,
            "current_step": "准备训练...",
        }

        mock_background_tasks = Mock()

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.create_task = AsyncMock(return_value=mock_task_id)
            mock_service.get_task = Mock(return_value=mock_task)

            # Act
            response = await create_training_task(request_data, mock_background_tasks)

            # Assert
            assert response.task_id == mock_task_id
            assert response.status == "pending"
            assert response.progress == 0
            mock_service.create_task.assert_called_once()
            mock_background_tasks.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_training_task_with_pooled_training(self):
        """测试创建池化训练任务"""
        # Arrange
        request_data = MLTrainingTaskCreate(
            symbols=["000001", "000002", "300001"],
            start_date="2023-01-01",
            end_date="2023-12-31",
            model_type="lightgbm",
            target_period=10,
            enable_pooled_training=True,
            enable_ridge_baseline=True,
        )

        mock_task_id = "task_pooled_789"
        mock_task = {
            "task_id": mock_task_id,
            "status": "pending",
            "created_at": datetime.now(),
            "config": request_data.dict(),
            "progress": 0,
            "current_step": "准备训练...",
        }

        mock_background_tasks = Mock()

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.create_task = AsyncMock(return_value=mock_task_id)
            mock_service.get_task = Mock(return_value=mock_task)

            # Act
            response = await create_training_task(request_data, mock_background_tasks)

            # Assert
            assert response.task_id == mock_task_id
            assert response.status == "pending"

    @pytest.mark.asyncio
    async def test_create_training_task_service_error(self):
        """测试创建任务时服务异常"""
        # Arrange
        request_data = MLTrainingTaskCreate(
            symbol="000001", start_date="2023-01-01", end_date="2023-12-31", model_type="lightgbm"
        )

        mock_background_tasks = Mock()

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.create_task = AsyncMock(side_effect=Exception("数据库连接失败"))

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_training_task(request_data, mock_background_tasks)

            assert exc_info.value.status_code == 500
            assert "数据库连接失败" in str(exc_info.value.detail)


class TestGetTaskStatus:
    """测试 GET /api/ml/tasks/{task_id} 端点"""

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """测试成功获取任务状态"""
        # Arrange
        task_id = "task_123456"
        mock_task = {
            "task_id": task_id,
            "status": "completed",
            "created_at": datetime.now(),
            "completed_at": datetime.now(),
            "config": {"symbol": "000001"},
            "progress": 100,
            "current_step": "训练完成",
            "metrics": {"rmse": 0.05, "ic": 0.08},
        }

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.get_task = Mock(return_value=mock_task)

            # Act
            response = await get_task_status(task_id)

            # Assert
            assert response.task_id == task_id
            assert response.status == "completed"
            assert response.progress == 100
            assert response.metrics == {"rmse": 0.05, "ic": 0.08}

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """测试获取不存在的任务"""
        # Arrange
        task_id = "invalid_task"

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.get_task = Mock(return_value=None)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_task_status(task_id)

            assert exc_info.value.status_code == 404
            assert "任务不存在" in str(exc_info.value.detail)


class TestListTasks:
    """测试 GET /api/ml/tasks 端点"""

    @pytest.mark.asyncio
    async def test_list_tasks_all(self):
        """测试列出所有任务"""
        # Arrange
        mock_tasks = [
            {"task_id": "task_1", "status": "completed", "created_at": datetime.now(), "config": {"symbol": "000001"}},
            {"task_id": "task_2", "status": "running", "created_at": datetime.now(), "config": {"symbol": "000002"}},
            {"task_id": "task_3", "status": "pending", "created_at": datetime.now(), "config": {"symbol": "000003"}},
        ]

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.list_tasks = Mock(return_value=mock_tasks)

            # Act
            response = await list_tasks()

            # Assert
            assert response["total"] == 3
            assert len(response["tasks"]) == 3
            mock_service.list_tasks.assert_called_once_with(status=None, limit=50)

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(self):
        """测试按状态过滤任务"""
        # Arrange
        mock_tasks = [
            {"task_id": "task_1", "status": "completed", "created_at": datetime.now(), "config": {"symbol": "000001"}},
            {"task_id": "task_2", "status": "completed", "created_at": datetime.now(), "config": {"symbol": "000002"}},
        ]

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.list_tasks = Mock(return_value=mock_tasks)

            # Act
            response = await list_tasks(status="completed", limit=20)

            # Assert
            assert response["total"] == 2
            assert all(task.status == "completed" for task in response["tasks"])
            mock_service.list_tasks.assert_called_once_with(status="completed", limit=20)


class TestDeleteTask:
    """测试 DELETE /api/ml/tasks/{task_id} 端点"""

    @pytest.mark.asyncio
    async def test_delete_task_success(self):
        """测试成功删除任务"""
        # Arrange
        task_id = "task_123456"

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.delete_task = Mock(return_value=True)

            # Act
            response = await delete_task(task_id)

            # Assert
            assert response["message"] == "删除成功"
            assert response["task_id"] == task_id
            mock_service.delete_task.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self):
        """测试删除不存在的任务"""
        # Arrange
        task_id = "invalid_task"

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.delete_task = Mock(return_value=False)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await delete_task(task_id)

            assert exc_info.value.status_code == 404
            assert "任务不存在" in str(exc_info.value.detail)


class TestPredict:
    """测试 POST /api/ml/predict 端点"""

    @pytest.mark.asyncio
    async def test_predict_with_experiment_id(self):
        """测试使用实验 ID 进行预测"""
        # Arrange
        request_data = MLPredictionRequest(
            experiment_id=42, symbol="000001", start_date="2024-01-01", end_date="2024-01-31"
        )

        mock_predictions = {
            "predictions": [
                {"date": "2024-01-01", "prediction": 0.02, "actual": 0.015},
                {"date": "2024-01-02", "prediction": 0.01, "actual": 0.008},
            ],
            "metrics": {"ic": 0.85, "rank_ic": 0.78, "rmse": 0.012},
        }

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.predict_from_experiment = AsyncMock(return_value=mock_predictions)

            # Act
            response = await predict(request_data)

            # Assert
            assert len(response.predictions) == 2
            assert response.metrics["ic"] == 0.85
            mock_service.predict_from_experiment.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_with_model_id(self):
        """测试使用模型 ID 进行预测（向后兼容）"""
        # Arrange
        request_data = MLPredictionRequest(
            model_id="task_123456", symbol="000001", start_date="2024-01-01", end_date="2024-01-31"
        )

        mock_predictions = {
            "predictions": [{"date": "2024-01-01", "prediction": 0.02, "actual": 0.015}],
            "metrics": {"ic": 0.85, "rank_ic": 0.78},
        }

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.predict = AsyncMock(return_value=mock_predictions)

            # Act
            response = await predict(request_data)

            # Assert
            assert len(response.predictions) == 1
            assert response.metrics["ic"] == 0.85

    @pytest.mark.asyncio
    async def test_predict_missing_identifiers(self):
        """测试缺少模型标识符"""
        # Arrange
        request_data = MLPredictionRequest(
            symbol="000001", start_date="2024-01-01", end_date="2024-01-31"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await predict(request_data)

        assert exc_info.value.status_code == 400
        assert "必须提供 experiment_id 或 model_id" in str(exc_info.value.detail)


class TestListModels:
    """测试 GET /api/ml/models 端点"""

    @pytest.mark.asyncio
    async def test_list_models_success(self):
        """测试成功列出模型"""
        # Arrange
        mock_models = [
            {
                "id": 1,
                "model_id": "task_123",
                "symbol": "000001",
                "model_type": "lightgbm",
                "metrics": {"rmse": 0.05, "ic": 0.08},
                "trained_at": "2024-01-01",
            },
            {
                "id": 2,
                "model_id": "task_456",
                "symbol": "000002",
                "model_type": "lightgbm",
                "metrics": {"rmse": 0.04, "ic": 0.10},
                "trained_at": "2024-01-02",
            },
        ]

        # Mock 数据库查询
        mock_db_results = [
            (
                1,
                None,
                "exp_1",
                "task_123",
                {"symbol": "000001", "model_type": "lightgbm"},
                {"rmse": 0.05, "ic": 0.08},
                None,
                None,
                "/path/to/model1.pkl",
                datetime(2024, 1, 1),
                None,
                datetime(2024, 1, 1),
            )
        ]

        with (
            patch("src.database.db_manager.get_database") as mock_get_db,
            patch(
                "app.api.endpoints.ml.asyncio.to_thread",
                new=AsyncMock(side_effect=[[[1]], mock_db_results]),  # 第一次返回count，第二次返回数据
            ),
        ):
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Act
            response = await list_models(page=1, page_size=20)

            # Assert
            assert "total" in response
            assert "models" in response
            assert response["page"] == 1
            assert response["page_size"] == 20

    @pytest.mark.asyncio
    async def test_list_models_with_filters(self):
        """测试使用过滤条件列出模型"""
        # Arrange
        with (
            patch("src.database.db_manager.get_database") as mock_get_db,
            patch("app.api.endpoints.ml.asyncio.to_thread", new=AsyncMock(side_effect=[[[0]], []])),  # count=0, 空结果
        ):
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Act
            response = await list_models(
                symbol="000001",
                model_type="lightgbm",
                source="manual_training",
                page=1,
                page_size=10,
            )

            # Assert
            assert "total" in response
            assert "models" in response


class TestGetAvailableFeatures:
    """测试 GET /api/ml/features/available 端点"""

    @pytest.mark.asyncio
    async def test_get_available_features_success(self):
        """测试成功获取可用特征列表"""
        # Act
        response = await get_available_features()

        # Assert
        assert "technical_indicators" in response
        assert "alpha_factors" in response
        assert "MA" in response["technical_indicators"]
        assert "MOMENTUM" in response["alpha_factors"]
        assert isinstance(response["technical_indicators"]["MA"], dict)
        assert "label" in response["technical_indicators"]["MA"]
        assert "params" in response["technical_indicators"]["MA"]


class TestGetFeatureSnapshot:
    """测试 GET /api/ml/features/snapshot 端点"""

    @pytest.mark.asyncio
    async def test_get_feature_snapshot_missing_model_id(self):
        """测试缺少模型 ID"""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_feature_snapshot(symbol="000001", date="2024-01-01", model_id=None)

        assert exc_info.value.status_code == 400
        assert "请先选择一个模型" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_feature_snapshot_model_not_found(self):
        """测试模型文件不存在"""
        # Arrange
        with patch("os.path.exists", return_value=False):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_feature_snapshot(symbol="000001", date="2024-01-01", model_id="task_123")

            assert exc_info.value.status_code == 404
            assert "没有保存特征数据" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_feature_snapshot_success(self):
        """测试成功获取特征快照"""
        # Arrange

        import pandas as pd

        mock_features_data = {
            "X": pd.DataFrame(
                {"feature_1": [0.1, 0.2, 0.3], "feature_2": [0.4, 0.5, 0.6]},
                index=pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"]),
            ),
            "y": pd.Series(
                [0.01, 0.02, 0.03],
                index=pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-03"]),
            ),
        }

        def mock_pickle_load(f):
            return mock_features_data

        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", MagicMock()),
            patch("pickle.load", side_effect=mock_pickle_load),
        ):
            # Act
            response = await get_feature_snapshot(
                symbol="000001", date="2024-01-01", model_id="task_123"
            )

            # Assert
            assert "date" in response
            assert "features" in response
            assert "target" in response
            assert response["date"] == "2024-01-01"
            assert "feature_1" in response["features"]
            assert "feature_2" in response["features"]


class TestStreamTaskProgress:
    """测试 GET /api/ml/tasks/{task_id}/stream 端点"""

    @pytest.mark.asyncio
    async def test_stream_task_progress_task_not_found(self):
        """测试任务不存在"""
        # Arrange
        task_id = "invalid_task"

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.get_task = Mock(return_value=None)

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await stream_task_progress(task_id)

            assert exc_info.value.status_code == 404
            assert "任务不存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_stream_task_progress_success(self):
        """测试成功流式推送进度（仅验证响应类型）"""
        # Arrange
        task_id = "task_123456"
        mock_task = {
            "task_id": task_id,
            "status": "running",
            "progress": 50,
            "current_step": "训练中...",
        }

        with patch("app.api.endpoints.ml.ml_service") as mock_service:
            mock_service.get_task = Mock(return_value=mock_task)

            # Act
            response = await stream_task_progress(task_id)

            # Assert
            assert response is not None
            # StreamingResponse 的详细测试需要异步生成器支持
