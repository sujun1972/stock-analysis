"""
TrainingTaskManager 单元测试

测试 training_task_manager.py 中的核心方法：
- create_task
- run_training
- get_task
- list_tasks
- cancel_task
- delete_task
- _run_single_stock_training
- _run_pooled_training

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, Mock, mock_open
from datetime import datetime
from pathlib import Path
import tempfile

from app.services.training_task_manager import TrainingTaskManager


class TestTrainingTaskManagerInit:
    """测试 TrainingTaskManager 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Arrange & Act
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            # Assert
            assert manager.tasks == {}
            assert manager.models_dir == Path('/data/models/ml_models')

    def test_init_with_custom_models_dir(self):
        """测试自定义模型目录初始化"""
        # Arrange
        custom_dir = Path("/tmp/test_models")

        # Act
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager(models_dir=custom_dir)

            # Assert
            assert manager.models_dir == custom_dir

    def test_load_existing_metadata(self):
        """测试加载已存在的任务元数据"""
        # Arrange
        mock_tasks = {
            'task_1': {'task_id': 'task_1', 'status': 'completed'},
            'task_2': {'task_id': 'task_2', 'status': 'pending'}
        }
        mock_file_content = json.dumps(mock_tasks)

        with patch('app.services.training_task_manager.DatabaseManager'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=mock_file_content)):
            # Act
            manager = TrainingTaskManager()

            # Assert
            assert len(manager.tasks) == 2
            assert 'task_1' in manager.tasks


class TestCreateTask:
    """测试创建训练任务"""

    @pytest.mark.asyncio
    async def test_create_task_success(self):
        """测试成功创建任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            config = {
                'symbol': '000001',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'model_type': 'lightgbm',
                'target_period': 5
            }

            # Act
            task_id = await manager.create_task(config)

            # Assert
            assert task_id in manager.tasks
            task = manager.tasks[task_id]
            assert task['status'] == 'pending'
            assert task['progress'] == 0
            assert task['config'] == config
            assert task['current_step'] == '准备训练...'
            assert 'created_at' in task
            manager._save_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_generates_unique_id(self):
        """测试创建任务生成唯一 ID"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            config = {'symbol': '000001'}

            # Act
            task_id_1 = await manager.create_task(config)
            task_id_2 = await manager.create_task(config)

            # Assert
            assert task_id_1 != task_id_2
            assert len(manager.tasks) == 2


class TestRunTraining:
    """测试执行训练任务"""

    @pytest.mark.asyncio
    async def test_run_training_task_not_found(self):
        """测试训练任务不存在"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            # Act & Assert
            with pytest.raises(ValueError, match="任务不存在"):
                await manager.run_training('invalid_task_id')

    @pytest.mark.asyncio
    async def test_run_training_success(self):
        """测试成功执行训练"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            # 创建任务
            task_id = await manager.create_task({'symbol': '000001'})

            # Mock _run_training 方法
            mock_result = {
                'metrics': {'rmse': 0.05, 'ic': 0.08},
                'model_path': '/path/to/model.pkl'
            }

            with patch.object(manager, '_run_training', new=AsyncMock()):
                # Act
                await manager.run_training(task_id)

                # Assert
                task = manager.tasks[task_id]
                assert task['status'] == 'completed'
                assert task['progress'] == 100
                assert 'completed_at' in task

    @pytest.mark.asyncio
    async def test_run_training_failure(self):
        """测试训练失败"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            # 创建任务
            task_id = await manager.create_task({'symbol': '000001'})

            # Mock _run_training 抛出异常
            with patch.object(manager, '_run_training', new=AsyncMock(side_effect=Exception("训练失败"))):
                # Act & Assert
                with pytest.raises(Exception, match="训练失败"):
                    await manager.run_training(task_id)

                # 验证任务状态
                task = manager.tasks[task_id]
                assert task['status'] == 'failed'
                assert task['error'] == '训练失败'
                assert task['error_message'] == '训练失败'
                assert 'failed_at' in task


class TestRunSingleStockTraining:
    """测试单股票训练"""

    @pytest.mark.asyncio
    async def test_run_single_stock_training_success(self):
        """测试成功执行单股票训练"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            # 创建任务
            config = {
                'symbol': '000001',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'model_type': 'lightgbm',
                'target_period': 5
            }
            task_id = await manager.create_task(config)

            # Mock CoreTrainingService
            mock_training_result = {
                'metrics': {'rmse': 0.05, 'ic': 0.08, 'r2': 0.75},
                'model_path': '/path/to/model.pkl',
                'feature_importance': {'feature_1': 0.3, 'feature_2': 0.2}
            }

            with patch('app.services.training_task_manager.CoreTrainingService') as mock_core, \
                 patch('asyncio.to_thread', new=AsyncMock(return_value=mock_training_result)):
                # Act
                await manager._run_single_stock_training(task_id)

                # Assert
                task = manager.tasks[task_id]
                assert task['metrics'] == mock_training_result['metrics']
                assert task['model_path'] == str(mock_training_result['model_path'])
                assert task['feature_importance'] == mock_training_result['feature_importance']
                assert task['progress'] == 100
                assert task['has_baseline'] is False


class TestRunPooledTraining:
    """测试池化训练"""

    @pytest.mark.asyncio
    async def test_run_pooled_training_success(self):
        """测试成功执行池化训练"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            # 创建池化训练任务
            config = {
                'symbols': ['000001', '000002', '300001'],
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'model_type': 'lightgbm',
                'target_period': 10,
                'enable_pooled_training': True,
                'enable_ridge_baseline': True
            }
            task_id = await manager.create_task(config)

            # Mock PooledTrainingPipeline
            mock_pipeline_result = {
                'lgb_metrics': {
                    'test_ic': 0.12,
                    'test_rank_ic': 0.10,
                    'test_mae': 0.03,
                    'test_r2': 0.68,
                    'train_ic': 0.15,
                    'valid_ic': 0.13
                },
                'lgb_model_path': '/path/to/lgb_model.pkl',
                'has_baseline': True,
                'ridge_metrics': {'test_ic': 0.08, 'test_rank_ic': 0.06},
                'comparison_result': {'winner': 'lightgbm', 'improvement': 0.04},
                'recommendation': 'lightgbm',
                'total_samples': 5000,
                'successful_symbols': ['000001', '000002', '300001'],
                'feature_importance': {'feature_1': 0.3}
            }

            with patch('app.services.training_task_manager.PooledTrainingPipeline') as mock_pipeline, \
                 patch('asyncio.to_thread', new=AsyncMock(return_value=mock_pipeline_result)), \
                 patch.object(manager, '_save_pooled_experiment_to_db', new=AsyncMock(return_value=None)):
                # Act
                await manager._run_pooled_training(task_id)

                # Assert
                task = manager.tasks[task_id]
                assert task['metrics']['ic'] == 0.12
                assert task['metrics']['rank_ic'] == 0.10
                assert task['has_baseline'] is True
                assert task['recommendation'] == 'lightgbm'
                assert task['total_samples'] == 5000
                assert len(task['successful_symbols']) == 3
                assert task['progress'] == 100


class TestGetTask:
    """测试获取任务信息"""

    def test_get_task_success(self):
        """测试成功获取任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            task_id = 'test_task_123'
            manager.tasks[task_id] = {
                'task_id': task_id,
                'status': 'completed',
                'progress': 100
            }

            # Act
            result = manager.get_task(task_id)

            # Assert
            assert result is not None
            assert result['task_id'] == task_id
            assert result['status'] == 'completed'

    def test_get_task_not_found(self):
        """测试获取不存在的任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            # Act
            result = manager.get_task('invalid_task_id')

            # Assert
            assert result is None


class TestListTasks:
    """测试列出任务"""

    def test_list_tasks_all(self):
        """测试列出所有任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager.tasks = {
                'task_1': {'task_id': 'task_1', 'status': 'completed', 'created_at': '2024-01-01'},
                'task_2': {'task_id': 'task_2', 'status': 'running', 'created_at': '2024-01-02'},
                'task_3': {'task_id': 'task_3', 'status': 'pending', 'created_at': '2024-01-03'}
            }

            # Act
            result = manager.list_tasks()

            # Assert
            assert result['total'] == 3
            assert len(result['tasks']) == 3
            # 验证按创建时间倒序排列
            assert result['tasks'][0]['task_id'] == 'task_3'

    def test_list_tasks_with_status_filter(self):
        """测试按状态过滤任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager.tasks = {
                'task_1': {'task_id': 'task_1', 'status': 'completed', 'created_at': '2024-01-01'},
                'task_2': {'task_id': 'task_2', 'status': 'running', 'created_at': '2024-01-02'},
                'task_3': {'task_id': 'task_3', 'status': 'completed', 'created_at': '2024-01-03'}
            }

            # Act
            result = manager.list_tasks(status='completed')

            # Assert
            assert result['total'] == 2
            assert len(result['tasks']) == 2
            assert all(task['status'] == 'completed' for task in result['tasks'])

    def test_list_tasks_with_pagination(self):
        """测试分页列出任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager.tasks = {
                f'task_{i}': {'task_id': f'task_{i}', 'status': 'completed', 'created_at': f'2024-01-{i:02d}'}
                for i in range(1, 51)
            }

            # Act
            result = manager.list_tasks(limit=10, offset=10)

            # Assert
            assert result['total'] == 50
            assert len(result['tasks']) == 10
            assert result['limit'] == 10
            assert result['offset'] == 10


class TestCancelTask:
    """测试取消任务"""

    def test_cancel_task_success(self):
        """测试成功取消任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            task_id = 'test_task'
            manager.tasks[task_id] = {
                'task_id': task_id,
                'status': 'pending'
            }

            # Act
            manager.cancel_task(task_id)

            # Assert
            assert manager.tasks[task_id]['status'] == 'cancelled'
            assert 'cancelled_at' in manager.tasks[task_id]
            manager._save_metadata.assert_called_once()

    def test_cancel_task_invalid_status(self):
        """测试取消已完成的任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            task_id = 'test_task'
            manager.tasks[task_id] = {
                'task_id': task_id,
                'status': 'completed'
            }

            # Act & Assert
            with pytest.raises(ValueError, match="任务无法取消"):
                manager.cancel_task(task_id)

    def test_cancel_task_not_found(self):
        """测试取消不存在的任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            # Act & Assert
            with pytest.raises(ValueError, match="任务不存在"):
                manager.cancel_task('invalid_task')


class TestDeleteTask:
    """测试删除任务"""

    def test_delete_task_success(self):
        """测试成功删除任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager._save_metadata = Mock()

            task_id = 'test_task'
            manager.tasks[task_id] = {
                'task_id': task_id,
                'status': 'completed'
            }

            # Act
            manager.delete_task(task_id)

            # Assert
            assert task_id not in manager.tasks
            manager._save_metadata.assert_called_once()

    def test_delete_task_not_found(self):
        """测试删除不存在的任务"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()

            # Act & Assert
            with pytest.raises(ValueError, match="任务不存在"):
                manager.delete_task('invalid_task')


class TestSaveAndLoadMetadata:
    """测试元数据保存和加载"""

    def test_save_metadata_success(self):
        """测试成功保存元数据"""
        # Arrange
        with patch('app.services.training_task_manager.DatabaseManager'):
            manager = TrainingTaskManager()
            manager.tasks = {
                'task_1': {'task_id': 'task_1', 'status': 'completed'}
            }

            mock_file = mock_open()
            with patch('builtins.open', mock_file):
                # Act
                manager._save_metadata()

                # Assert
                mock_file.assert_called_once()
                # 验证写入了 JSON 数据
                handle = mock_file()
                handle.write.assert_called()
