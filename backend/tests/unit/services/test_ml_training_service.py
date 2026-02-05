"""
MLTrainingService 单元测试

测试 ml_training_service.py 中的所有方法：
- create_task
- run_training / start_training
- get_task
- list_tasks
- cancel_task
- delete_task
- predict
- batch_predict
- predict_from_experiment

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ml_training_service import MLTrainingService


class TestMLTrainingServiceInit:
    """测试 MLTrainingService 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Act
        service = MLTrainingService()

        # Assert
        assert service.task_manager is not None
        assert service.predictor is not None

    def test_init_with_custom_models_dir(self):
        """测试自定义模型目录初始化"""
        # Arrange
        custom_dir = Path("/tmp/test_models")

        # Act
        service = MLTrainingService(models_dir=custom_dir)

        # Assert
        assert service.task_manager is not None
        assert service.task_manager.models_dir == custom_dir


class TestCreateTask:
    """测试创建训练任务"""

    @pytest.mark.asyncio
    async def test_create_task_success(self):
        """测试成功创建任务"""
        # Arrange
        service = MLTrainingService()
        config = {
            "symbol": "000001",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "model_type": "lightgbm",
            "target_period": 5,
        }

        mock_task_id = "task_123456"

        with patch.object(
            service.task_manager, "create_task", new=AsyncMock(return_value=mock_task_id)
        ):
            # Act
            task_id = await service.create_task(config)

            # Assert
            assert task_id == mock_task_id
            service.task_manager.create_task.assert_called_once_with(config)

    @pytest.mark.asyncio
    async def test_create_task_with_pooled_training(self):
        """测试创建池化训练任务"""
        # Arrange
        service = MLTrainingService()
        config = {
            "symbols": ["000001", "000002", "300001"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "model_type": "lightgbm",
            "target_period": 10,
            "enable_pooled_training": True,
            "enable_ridge_baseline": True,
        }

        mock_task_id = "task_pooled_789"

        with patch.object(
            service.task_manager, "create_task", new=AsyncMock(return_value=mock_task_id)
        ):
            # Act
            task_id = await service.create_task(config)

            # Assert
            assert task_id == mock_task_id
            service.task_manager.create_task.assert_called_once_with(config)


class TestRunTraining:
    """测试执行训练任务"""

    @pytest.mark.asyncio
    async def test_run_training_success(self):
        """测试成功执行训练"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"

        with patch.object(service.task_manager, "run_training", new=AsyncMock()):
            # Act
            await service.run_training(task_id)

            # Assert
            service.task_manager.run_training.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_start_training_alias(self):
        """测试 start_training 别名方法"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"

        with patch.object(service.task_manager, "run_training", new=AsyncMock()):
            # Act
            await service.start_training(task_id)

            # Assert
            service.task_manager.run_training.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_run_training_task_not_found(self):
        """测试训练任务不存在"""
        # Arrange
        service = MLTrainingService()
        task_id = "invalid_task"

        with patch.object(
            service.task_manager,
            "run_training",
            new=AsyncMock(side_effect=ValueError("任务不存在")),
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="任务不存在"):
                await service.run_training(task_id)


class TestGetTask:
    """测试获取任务信息"""

    def test_get_task_success(self):
        """测试成功获取任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"
        mock_task = {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "metrics": {"rmse": 0.05, "ic": 0.08},
        }

        with patch.object(service.task_manager, "get_task", return_value=mock_task):
            # Act
            result = service.get_task(task_id)

            # Assert
            assert result == mock_task
            assert result["task_id"] == task_id
            assert result["status"] == "completed"
            service.task_manager.get_task.assert_called_once_with(task_id)

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "invalid_task"

        with patch.object(service.task_manager, "get_task", return_value=None):
            # Act
            result = service.get_task(task_id)

            # Assert
            assert result is None


class TestListTasks:
    """测试列出任务"""

    def test_list_tasks_all(self):
        """测试列出所有任务"""
        # Arrange
        service = MLTrainingService()
        mock_tasks_response = {
            "tasks": [
                {"task_id": "task_1", "status": "completed"},
                {"task_id": "task_2", "status": "running"},
                {"task_id": "task_3", "status": "pending"},
            ],
            "total": 3,
            "limit": 100,
            "offset": 0,
        }

        with patch.object(service.task_manager, "list_tasks", return_value=mock_tasks_response):
            # Act
            result = service.list_tasks()

            # Assert
            assert result["total"] == 3
            assert len(result["tasks"]) == 3
            service.task_manager.list_tasks.assert_called_once_with(None, 100, 0)

    def test_list_tasks_with_status_filter(self):
        """测试按状态过滤任务"""
        # Arrange
        service = MLTrainingService()
        mock_tasks_response = {
            "tasks": [
                {"task_id": "task_1", "status": "completed"},
                {"task_id": "task_2", "status": "completed"},
            ],
            "total": 2,
            "limit": 100,
            "offset": 0,
        }

        with patch.object(service.task_manager, "list_tasks", return_value=mock_tasks_response):
            # Act
            result = service.list_tasks(status="completed")

            # Assert
            assert result["total"] == 2
            assert all(task["status"] == "completed" for task in result["tasks"])
            service.task_manager.list_tasks.assert_called_once_with("completed", 100, 0)

    def test_list_tasks_with_pagination(self):
        """测试分页列出任务"""
        # Arrange
        service = MLTrainingService()
        mock_tasks_response = {
            "tasks": [{"task_id": f"task_{i}", "status": "completed"} for i in range(20, 40)],
            "total": 100,
            "limit": 20,
            "offset": 20,
        }

        with patch.object(service.task_manager, "list_tasks", return_value=mock_tasks_response):
            # Act
            result = service.list_tasks(limit=20, offset=20)

            # Assert
            assert result["total"] == 100
            assert len(result["tasks"]) == 20
            assert result["limit"] == 20
            assert result["offset"] == 20
            service.task_manager.list_tasks.assert_called_once_with(None, 20, 20)


class TestCancelTask:
    """测试取消任务"""

    def test_cancel_task_success(self):
        """测试成功取消任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"

        with patch.object(service.task_manager, "cancel_task"):
            # Act
            service.cancel_task(task_id)

            # Assert
            service.task_manager.cancel_task.assert_called_once_with(task_id)

    def test_cancel_task_invalid_status(self):
        """测试取消已完成的任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"

        with patch.object(
            service.task_manager, "cancel_task", side_effect=ValueError("任务无法取消")
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="任务无法取消"):
                service.cancel_task(task_id)


class TestDeleteTask:
    """测试删除任务"""

    def test_delete_task_success(self):
        """测试成功删除任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "task_123456"

        with patch.object(service.task_manager, "delete_task"):
            # Act
            service.delete_task(task_id)

            # Assert
            service.task_manager.delete_task.assert_called_once_with(task_id)

    def test_delete_task_not_found(self):
        """测试删除不存在的任务"""
        # Arrange
        service = MLTrainingService()
        task_id = "invalid_task"

        with patch.object(
            service.task_manager, "delete_task", side_effect=ValueError("任务不存在")
        ):
            # Act & Assert
            with pytest.raises(ValueError, match="任务不存在"):
                service.delete_task(task_id)


class TestPredict:
    """测试模型预测"""

    @pytest.mark.asyncio
    async def test_predict_with_model_id(self):
        """测试使用 model_id 进行预测"""
        # Arrange
        service = MLTrainingService()
        mock_predictions = {
            "predictions": [
                {"date": "2024-01-01", "prediction": 0.02, "actual": 0.015},
                {"date": "2024-01-02", "prediction": 0.01, "actual": 0.008},
            ],
            "metrics": {"ic": 0.85, "rank_ic": 0.78},
        }

        with patch.object(
            service.predictor, "predict", new=AsyncMock(return_value=mock_predictions)
        ):
            # Act
            result = await service.predict(
                symbol="000001",
                start_date="2024-01-01",
                end_date="2024-01-31",
                model_id="task_123456",
            )

            # Assert
            assert len(result["predictions"]) == 2
            assert "metrics" in result
            assert result["metrics"]["ic"] == 0.85

    @pytest.mark.asyncio
    async def test_predict_with_experiment_id(self):
        """测试使用 experiment_id 进行预测"""
        # Arrange
        service = MLTrainingService()
        mock_predictions = {
            "predictions": [{"date": "2024-01-01", "prediction": 0.02, "actual": 0.015}],
            "metrics": {"ic": 0.85, "rank_ic": 0.78},
        }

        with patch.object(
            service.predictor, "predict", new=AsyncMock(return_value=mock_predictions)
        ):
            # Act
            result = await service.predict(
                symbol="000001", start_date="2024-01-01", end_date="2024-01-31", experiment_id=42
            )

            # Assert
            assert "predictions" in result
            assert "metrics" in result


class TestBatchPredict:
    """测试批量预测"""

    @pytest.mark.asyncio
    async def test_batch_predict_success(self):
        """测试成功批量预测多只股票"""
        # Arrange
        service = MLTrainingService()
        symbols = ["000001", "000002", "300001"]
        mock_batch_results = {
            "results": {
                "000001": {"predictions": [], "metrics": {"ic": 0.85}},
                "000002": {"predictions": [], "metrics": {"ic": 0.82}},
                "300001": {"predictions": [], "metrics": {"ic": 0.88}},
            },
            "summary": {"total": 3, "successful": 3, "failed": 0, "avg_ic": 0.85},
        }

        with patch.object(
            service.predictor, "batch_predict", new=AsyncMock(return_value=mock_batch_results)
        ):
            # Act
            result = await service.batch_predict(
                symbols=symbols, start_date="2024-01-01", end_date="2024-01-31", experiment_id=42
            )

            # Assert
            assert result["summary"]["total"] == 3
            assert result["summary"]["successful"] == 3
            assert len(result["results"]) == 3


class TestPredictFromExperiment:
    """测试从实验表预测（向后兼容）"""

    @pytest.mark.asyncio
    async def test_predict_from_experiment_success(self):
        """测试使用实验 ID 进行预测"""
        # Arrange
        service = MLTrainingService()
        mock_predictions = {
            "predictions": [{"date": "2024-01-01", "prediction": 0.02, "actual": 0.015}],
            "metrics": {"ic": 0.85, "rank_ic": 0.78},
        }

        with patch.object(
            service.predictor, "predict", new=AsyncMock(return_value=mock_predictions)
        ):
            # Act
            result = await service.predict_from_experiment(
                experiment_id=42, symbol="000001", start_date="2024-01-01", end_date="2024-01-31"
            )

            # Assert
            assert "predictions" in result
            assert "metrics" in result
            assert result["metrics"]["ic"] == 0.85
