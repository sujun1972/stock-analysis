"""
任务历史记录辅助服务

提供统一的 Celery 任务历史记录创建功能，避免代码重复。
"""

import asyncio
from typing import Dict, Optional
from loguru import logger

from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository


class TaskHistoryHelper:
    """
    任务历史记录辅助类

    职责:
    - 统一创建 Celery 任务历史记录
    - 封装重复的任务记录逻辑
    - 提供简洁的 API 接口

    使用示例:
        >>> helper = TaskHistoryHelper()
        >>> await helper.create_task_record(
        ...     celery_task_id='a1b2c3d4-...',
        ...     task_name='tasks.sync_moneyflow',
        ...     display_name='个股资金流向',
        ...     task_type='data_sync',
        ...     user_id=1,
        ...     task_params={'ts_code': '000001.SZ'},
        ...     source='moneyflow_page'
        ... )
    """

    def __init__(self):
        self.task_repo = CeleryTaskHistoryRepository()
        logger.debug("✓ TaskHistoryHelper initialized")

    async def create_task_record(
        self,
        celery_task_id: str,
        task_name: str,
        display_name: str,
        task_type: str = 'data_sync',
        user_id: Optional[int] = None,
        task_params: Optional[Dict] = None,
        source: Optional[str] = None
    ) -> Dict:
        """
        创建任务历史记录

        Args:
            celery_task_id: Celery 任务ID (UUID格式)
            task_name: 任务名称 (如 'tasks.sync_moneyflow')
            display_name: 显示名称 (如 '个股资金流向')
            task_type: 任务类型 (默认 'data_sync')
            user_id: 用户ID (可选)
            task_params: 任务参数字典 (可选)
            source: 触发源页面 (可选，如 'moneyflow_page')

        Returns:
            包含 celery_task_id, task_name, display_name, status 的字典

        Examples:
            >>> helper = TaskHistoryHelper()
            >>> result = await helper.create_task_record(
            ...     celery_task_id='abc-123',
            ...     task_name='tasks.sync_moneyflow',
            ...     display_name='个股资金流向',
            ...     user_id=1,
            ...     task_params={'ts_code': '000001.SZ'},
            ...     source='moneyflow_page'
            ... )
            >>> print(result['status'])  # 'pending'
        """
        try:
            # 构建元数据
            metadata = {
                "trigger": "manual"
            }
            if source:
                metadata["source"] = source

            # 调用 Repository 创建记录
            await asyncio.to_thread(
                self.task_repo.create_task_history,
                celery_task_id=celery_task_id,
                task_name=task_name,
                display_name=display_name,
                task_type=task_type,
                user_id=user_id,
                params=task_params,
                metadata=metadata
            )

            logger.info(f"任务历史记录已创建: {celery_task_id} - {display_name}")

            # 返回任务信息
            return {
                "celery_task_id": celery_task_id,
                "task_name": task_name,
                "display_name": display_name,
                "status": "pending"
            }

        except Exception as e:
            logger.error(f"创建任务历史记录失败: {e}")
            raise
