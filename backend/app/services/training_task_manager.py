"""
训练任务管理器
负责训练任务的生命周期管理
"""

import asyncio
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from database.db_manager import DatabaseManager
from app.services.core_training import CoreTrainingService


class TrainingTaskManager:
    """
    训练任务管理器

    职责：
    - 创建和管理训练任务
    - 跟踪任务状态
    - 存储任务元数据
    - 执行训练流程
    """

    def __init__(self, models_dir: Optional[Path] = None, db: Optional[DatabaseManager] = None):
        """
        初始化任务管理器

            db: DatabaseManager 实例（可选，用于依赖注入）
        Args:
            models_dir: 模型存储目录
        """
        self.tasks: Dict[str, Dict[str, Any]] = {}  # 内存中的任务状态
        self.models_dir = models_dir or Path('/data/models/ml_models')
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 任务元数据存储
        self.metadata_file = self.models_dir / 'tasks_metadata.json'
        self._load_metadata()

        # 数据库连接
        self.db = db or DatabaseManager()

    def _load_metadata(self):
        """加载任务元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.tasks = json.load(f)
                logger.info(f"✓ 加载了 {len(self.tasks)} 个历史任务")
            except Exception as e:
                logger.error(f"加载元数据失败: {e}")
                self.tasks = {}

    def _save_metadata(self):
        """保存任务元数据"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.tasks, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"保存元数据失败: {e}")

    async def create_task(self, config: Dict[str, Any]) -> str:
        """
        创建训练任务

        Args:
            config: 训练配置

        Returns:
            task_id: 任务ID
        """
        task_id = str(uuid.uuid4())

        task = {
            'task_id': task_id,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'config': config,
            'progress': 0,
            'metrics': {},
            'error': None
        }

        self.tasks[task_id] = task
        self._save_metadata()

        logger.info(f"✓ 创建训练任务: {task_id}")
        return task_id

    async def run_training(self, task_id: str):
        """
        执行训练任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        # 更新任务状态
        task['status'] = 'running'
        task['started_at'] = datetime.now().isoformat()
        self._save_metadata()

        logger.info(f"🚀 开始训练任务: {task_id}")

        try:
            await self._run_training(task_id)

            # 训练成功
            task['status'] = 'completed'
            task['completed_at'] = datetime.now().isoformat()
            task['progress'] = 100

            logger.info(f"✓ 训练任务完成: {task_id}")

        except Exception as e:
            # 训练失败
            task['status'] = 'failed'
            task['error'] = str(e)
            task['failed_at'] = datetime.now().isoformat()

            logger.error(f"✗ 训练任务失败: {task_id} - {e}")
            raise

        finally:
            self._save_metadata()

    async def _run_training(self, task_id: str):
        """
        执行实际的训练过程

        Args:
            task_id: 任务ID
        """
        task = self.tasks[task_id]
        config = task['config']

        # 使用 CoreTrainingService 统一训练流程
        core_service = CoreTrainingService()

        # 准备训练配置
        training_config = {
            'symbol': config.get('symbol'),
            'start_date': config.get('start_date'),
            'end_date': config.get('end_date'),
            'model_type': config.get('model_type', 'lightgbm'),
            'target_period': config.get('target_period', 5),
            'scaler_type': config.get('scaler_type', 'robust'),
            'balance_samples': config.get('balance_samples', False),
            'model_params': config.get('model_params', {}),
            'use_async': True  # 使用异步模式
        }

        # 添加可选参数
        if 'seq_length' in config:
            training_config['seq_length'] = config['seq_length']
        if 'epochs' in config:
            training_config['epochs'] = config['epochs']

        logger.info(f"训练配置: {training_config}")

        # 执行训练
        result = await asyncio.to_thread(
            core_service.train_model,
            **training_config
        )

        # 保存训练结果
        task['metrics'] = result.get('metrics', {})
        task['model_path'] = str(result.get('model_path', ''))
        task['feature_importance'] = result.get('feature_importance', {})

        # 更新进度
        task['progress'] = 100

        logger.info(f"✓ 训练完成，模型路径: {task['model_path']}")

        self._save_metadata()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        列出任务

        Args:
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            任务列表和总数
        """
        # 过滤任务
        filtered_tasks = []
        for task in self.tasks.values():
            if status is None or task.get('status') == status:
                filtered_tasks.append(task)

        # 排序（按创建时间倒序）
        filtered_tasks.sort(
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )

        # 分页
        total = len(filtered_tasks)
        paginated_tasks = filtered_tasks[offset:offset + limit]

        return {
            'tasks': paginated_tasks,
            'total': total,
            'limit': limit,
            'offset': offset
        }

    def cancel_task(self, task_id: str):
        """
        取消任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        task = self.tasks[task_id]

        if task['status'] not in ['pending', 'running']:
            raise ValueError(f"任务无法取消，当前状态: {task['status']}")

        task['status'] = 'cancelled'
        task['cancelled_at'] = datetime.now().isoformat()
        self._save_metadata()

        logger.info(f"✓ 任务已取消: {task_id}")

    def delete_task(self, task_id: str):
        """
        删除任务

        Args:
            task_id: 任务ID
        """
        if task_id not in self.tasks:
            raise ValueError(f"任务不存在: {task_id}")

        del self.tasks[task_id]
        self._save_metadata()

        logger.info(f"✓ 任务已删除: {task_id}")
