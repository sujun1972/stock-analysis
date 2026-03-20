"""
定时任务执行服务

职责：
- 手动执行定时任务
- 查询任务执行状态
- 记录任务执行历史
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from app.repositories import ScheduledTaskRepository
from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
from app.repositories.task_execution_history_repository import TaskExecutionHistoryRepository
from app.core.exceptions import QueryError, DatabaseError
from .cron_service import CronService


class TaskExecutionService:
    """
    定时任务执行服务

    职责：
    - 手动执行任务
    - 获取任务执行状态
    - 记录执行历史
    """

    def __init__(self):
        self.scheduled_task_repo = ScheduledTaskRepository()
        self.celery_task_repo = CeleryTaskHistoryRepository()
        self.execution_history_repo = TaskExecutionHistoryRepository()
        self.cron_service = CronService()
        logger.debug("✓ TaskExecutionService initialized")

    async def execute_task_async(
        self,
        task_id: int,
        user_id: int
    ) -> Dict:
        """
        手动执行定时任务（异步提交到 Celery）

        Args:
            task_id: 任务ID
            user_id: 执行用户ID

        Returns:
            执行结果字典，包含 celery_task_id

        Raises:
            QueryError: 任务不存在
            DatabaseError: 执行失败

        Examples:
            >>> service = TaskExecutionService()
            >>> result = await service.execute_task_async(task_id=1, user_id=1)
            >>> print(result['celery_task_id'])
        """
        try:
            # 使用 ScheduledTaskRepository 查询任务配置
            task_config = await asyncio.to_thread(
                self.scheduled_task_repo.get_by_id,
                task_id
            )

            if not task_config:
                raise QueryError(
                    f"任务 {task_id} 不存在",
                    error_code="TASK_NOT_FOUND",
                    reason=f"Task ID {task_id} not found"
                )

            task_id_db = task_config['id']
            task_name = task_config['task_name']
            module = task_config['module']
            params = task_config.get('params', {})

            # 导入任务执行器
            from app.scheduler.task_executor import TaskExecutor
            executor = TaskExecutor()

            # 执行任务
            celery_task_id = await executor.execute_task(
                task_name=task_name,
                module=module,
                params=params or {}
            )

            # 记录执行历史到 task_execution_history 表
            result_summary = {
                "trigger": "manual",
                "celery_task_id": celery_task_id,
                "triggered_by": "admin"
            }

            execution_data = {
                'task_id': task_id_db,
                'task_name': task_name,
                'module': module,
                'status': 'running',
                'started_at': datetime.now(),
                'result_summary': result_summary
            }

            await asyncio.to_thread(
                self.execution_history_repo.create,
                execution_data
            )

            # 记录到 celery_task_history 表（用于任务面板显示）
            from app.scheduler import TaskMetadataService
            metadata_service = TaskMetadataService()
            display_name = metadata_service.get_friendly_name(module, task_name)

            task_metadata = {
                "trigger": "manual",
                "scheduled_task_id": task_id_db,
                "module": module
            }

            celery_task_data = {
                'celery_task_id': celery_task_id,
                'task_name': task_name,
                'display_name': display_name,
                'task_type': 'scheduler',
                'user_id': user_id,
                'status': 'pending',
                'params': params or {},
                'metadata': task_metadata,
                'created_at': datetime.now()
            }

            await asyncio.to_thread(
                self.celery_task_repo.create,
                celery_task_data
            )

            logger.info(f"✓ 手动执行定时任务: {task_name} (ID: {task_id_db}, Celery ID: {celery_task_id})")

            return {
                "task_id": task_id_db,
                "task_name": task_name,
                "celery_task_id": celery_task_id,
                "status": "submitted"
            }

        except QueryError:
            raise
        except Exception as e:
            logger.error(f"执行定时任务失败: {e}")
            raise DatabaseError(
                "执行定时任务失败",
                error_code="EXECUTE_TASK_FAILED",
                reason=str(e)
            )

    async def get_task_execution_status(
        self,
        task_id: int,
        celery_task_id: Optional[str] = None
    ) -> Dict:
        """
        获取任务执行状态

        Note:
            如果提供 celery_task_id，则从 Celery 获取实时状态
            否则从 task_execution_history 表获取最近执行状态

        Args:
            task_id: 数据库任务ID
            celery_task_id: Celery任务ID（可选）

        Returns:
            任务执行状态字典

        Examples:
            >>> service = TaskExecutionService()
            >>> status = await service.get_task_execution_status(1, "abc-123")
        """
        try:
            if celery_task_id:
                # 从 Celery 获取任务状态
                from app.celery_app import celery_app
                from celery.result import AsyncResult

                result = AsyncResult(celery_task_id, app=celery_app)

                status_map = {
                    'PENDING': 'pending',
                    'STARTED': 'running',
                    'SUCCESS': 'success',
                    'FAILURE': 'failed',
                    'RETRY': 'retrying',
                    'REVOKED': 'cancelled'
                }

                return {
                    "celery_task_id": celery_task_id,
                    "status": status_map.get(result.state, result.state.lower()),
                    "result": result.result if result.state == 'SUCCESS' else None,
                    "error": str(result.info) if result.state == 'FAILURE' else None,
                    "progress": result.info.get('progress', 0) if hasattr(result.info, 'get') else 0
                }

            # 使用 TaskExecutionHistoryRepository 获取最近的执行状态
            record = await asyncio.to_thread(
                self.execution_history_repo.get_latest_by_task_id,
                task_id
            )

            if not record:
                return {"status": "no_history", "message": "暂无执行历史"}

            return {
                "history_id": record['id'],
                "status": record['status'],
                "started_at": self.cron_service.format_datetime(record.get('started_at')),
                "completed_at": self.cron_service.format_datetime(record.get('completed_at')),
                "result": record.get('result_summary'),
                "error": record.get('error_message')
            }

        except Exception as e:
            logger.error(f"获取任务执行状态失败: {e}")
            raise QueryError(
                "获取任务执行��态失败",
                error_code="GET_STATUS_FAILED",
                reason=str(e)
            )
