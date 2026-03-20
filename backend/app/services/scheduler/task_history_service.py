"""
定时任务执行历史服务

职责：
- 查询任务执行历史
- 格式化历史数据
- 关联任务配置信息
"""

import asyncio
from typing import Dict, List
from loguru import logger

from app.repositories import ScheduledTaskRepository
from app.repositories.task_execution_history_repository import TaskExecutionHistoryRepository
from app.core.exceptions import QueryError
from .cron_service import CronService


class TaskHistoryService:
    """
    定时任务执行历史服务

    职责：
    - 查询任务执行历史
    - 格式化和关联配置信息
    """

    def __init__(self):
        self.execution_history_repo = TaskExecutionHistoryRepository()
        self.scheduled_task_repo = ScheduledTaskRepository()
        self.cron_service = CronService()
        logger.debug("✓ TaskHistoryService initialized")

    async def get_task_execution_history(
        self,
        task_id: int,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取任务执行历史（从 task_execution_history 表）

        Args:
            task_id: 任务ID
            limit: 返回记录数

        Returns:
            执行历史列表

        Examples:
            >>> service = TaskHistoryService()
            >>> history = await service.get_task_execution_history(1, limit=10)
        """
        try:
            # 使用 TaskExecutionHistoryRepository 查询
            records = await asyncio.to_thread(
                self.execution_history_repo.get_by_task_id,
                task_id=task_id,
                limit=limit
            )

            # 格式化日期字段
            history = []
            for record in records:
                history.append({
                    "id": record['id'],
                    "task_name": record['task_name'],
                    "module": record['module'],
                    "status": record['status'],
                    "started_at": self.cron_service.format_datetime(record.get('started_at')),
                    "completed_at": self.cron_service.format_datetime(record.get('completed_at')),
                    "duration_seconds": record.get('duration_seconds'),
                    "result_summary": record.get('result_summary'),
                    "error_message": record.get('error_message')
                })

            return history

        except Exception as e:
            logger.error(f"获取任务执行历史失败: {e}")
            raise QueryError(
                "获取任务执行历史失败",
                error_code="GET_HISTORY_FAILED",
                reason=str(e)
            )

    async def get_recent_execution_history(self, limit: int = 50) -> List[Dict]:
        """
        获取最近的任务执行历史（所有任务）

        Args:
            limit: 返回记录数

        Returns:
            执行历史列表

        Examples:
            >>> service = TaskHistoryService()
            >>> history = await service.get_recent_execution_history(limit=30)
        """
        try:
            # 使用 TaskExecutionHistoryRepository 查询
            records = await asyncio.to_thread(
                self.execution_history_repo.get_recent_executions,
                limit=limit
            )

            # 关联 scheduled_tasks 表获取 cron_expression
            # 批量查询任务配置
            task_ids = list({r['task_id'] for r in records if r.get('task_id')})
            task_config_map = {}

            if task_ids:
                for task_id in task_ids:
                    task_config = await asyncio.to_thread(
                        self.scheduled_task_repo.get_by_id,
                        task_id
                    )
                    if task_config:
                        task_config_map[task_id] = task_config

            # 格式化日期字段并关联 cron_expression
            history = []
            for record in records:
                task_id = record.get('task_id')
                task_config = task_config_map.get(task_id) if task_id else None

                history.append({
                    "id": record['id'],
                    "task_name": record['task_name'],
                    "module": record['module'],
                    "status": record['status'],
                    "started_at": self.cron_service.format_datetime(record.get('started_at')),
                    "completed_at": self.cron_service.format_datetime(record.get('completed_at')),
                    "duration_seconds": record.get('duration_seconds'),
                    "result_summary": record.get('result_summary'),
                    "error_message": record.get('error_message'),
                    "cron_expression": task_config.get('cron_expression') if task_config else None
                })

            return history

        except Exception as e:
            logger.error(f"获取最近执行历史失败: {e}")
            raise QueryError(
                "获取最近执行历史失败",
                error_code="GET_RECENT_HISTORY_FAILED",
                reason=str(e)
            )
