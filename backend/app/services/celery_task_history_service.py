"""
Celery 任务历史服务

业务逻辑层，负责任务历史的管理和统计。
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.repositories import CeleryTaskHistoryRepository


class CeleryTaskHistoryService:
    """
    Celery 任务历史服务

    职责:
    - 任务历史记录管理
    - 时间格式转换（数据库本地时间 <-> API UTC时间）
    - 业务逻辑编排
    """

    def __init__(self):
        """初始化服务"""
        self.task_history_repo = CeleryTaskHistoryRepository()
        logger.debug("✓ CeleryTaskHistoryService initialized")

    # ==================== 时间格式化 ====================

    @staticmethod
    def format_datetime_utc(dt: Optional[datetime]) -> Optional[str]:
        """
        格式化 datetime 为 UTC ISO 格式字符串

        Args:
            dt: datetime 对象

        Returns:
            ISO 8601 格式 + Z 后缀，例如 "2026-03-18T16:52:54Z"
        """
        if dt is None:
            return None
        return dt.isoformat() + 'Z' if dt else None

    def format_task_dict(self, task: Dict) -> Dict:
        """
        格式化任务字典，将 datetime 对象转换为 UTC 字符串

        Args:
            task: 任务字典

        Returns:
            格式化后的任务字典
        """
        if not task:
            return task

        # 复制字典，避免修改原始数据
        formatted = task.copy()

        # 转换时间字段
        time_fields = ['created_at', 'started_at', 'completed_at']
        for field in time_fields:
            if field in formatted and formatted[field]:
                formatted[field] = self.format_datetime_utc(formatted[field])

        return formatted

    # ==================== 查询操作 ====================

    async def get_task_by_id(self, celery_task_id: str) -> Optional[Dict]:
        """
        根据任务ID获取任务历史

        Args:
            celery_task_id: Celery 任务ID

        Returns:
            任务历史记录（格式化后）
        """
        task = await asyncio.to_thread(
            self.task_history_repo.get_by_task_id,
            celery_task_id
        )

        return self.format_task_dict(task) if task else None

    async def get_active_tasks(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        获取活跃任务列表

        Args:
            user_id: 用户ID（可选）

        Returns:
            活跃任务列表（格式化后）
        """
        tasks = await asyncio.to_thread(
            self.task_history_repo.get_active_tasks,
            user_id
        )

        return [self.format_task_dict(task) for task in tasks]

    async def get_recent_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """
        获取最近任务历史（带分页和筛选）

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            status: 按状态筛选（可选）
            task_type: 按任务类型筛选（可选）

        Returns:
            (格式化后的任务列表, 总数) 元组
        """
        tasks, total = await asyncio.to_thread(
            self.task_history_repo.get_recent_history,
            user_id,
            limit,
            offset,
            status,
            task_type
        )

        formatted_tasks = [self.format_task_dict(task) for task in tasks]
        return formatted_tasks, total

    async def get_statistics(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取任务统计信息

        Args:
            user_id: 用户ID（可选）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）

        Returns:
            统计信息字典
        """
        stats = await asyncio.to_thread(
            self.task_history_repo.get_statistics,
            user_id,
            start_date,
            end_date
        )

        return stats

    async def get_stale_tasks(self, user_id: int, minutes: int = 5) -> List[Dict]:
        """
        获取僵尸任务列表

        Args:
            user_id: 用户ID
            minutes: 超时分钟数

        Returns:
            僵尸任务列表（格式化后）
        """
        tasks = await asyncio.to_thread(
            self.task_history_repo.get_stale_tasks,
            user_id,
            minutes
        )

        return [self.format_task_dict(task) for task in tasks]

    # ==================== 写入操作 ====================

    async def create_task_history(
        self,
        celery_task_id: str,
        task_name: str,
        display_name: Optional[str] = None,
        task_type: str = 'other',
        user_id: Optional[int] = None,
        params: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        创建任务历史记录

        Args:
            celery_task_id: Celery 任务ID
            task_name: 任务名称（如 tasks.sync_moneyflow）
            display_name: 显示名称
            task_type: 任务类型
            user_id: 用户ID
            params: 任务参数
            metadata: 元数据

        Returns:
            创建的任务历史记录（格式化后）
        """
        task = await asyncio.to_thread(
            self.task_history_repo.create_task_history,
            celery_task_id,
            task_name,
            display_name,
            task_type,
            user_id,
            params,
            metadata
        )

        return self.format_task_dict(task)

    async def update_task_status(
        self,
        celery_task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        worker: Optional[str] = None
    ) -> Dict:
        """
        更新任务状态

        Args:
            celery_task_id: Celery 任务ID
            status: 任务状态
            progress: 进度 (0-100)
            started_at: 开始时间
            completed_at: 完成时间
            duration_ms: 耗时（毫秒）
            result: 任务结果
            error: 错误信息
            worker: Worker 名称

        Returns:
            更新后的任务历史记录（格式化后）
        """
        # 执行更新
        await asyncio.to_thread(
            self.task_history_repo.update_task_status,
            celery_task_id,
            status,
            progress,
            started_at,
            completed_at,
            duration_ms,
            result,
            error,
            worker
        )

        # 查询更新后的记录
        updated_task = await asyncio.to_thread(
            self.task_history_repo.get_by_task_id,
            celery_task_id
        )

        return self.format_task_dict(updated_task) if updated_task else {}

    async def delete_task_history(
        self,
        celery_task_id: str,
        user_id: Optional[int] = None
    ) -> int:
        """
        删除任务历史记录

        Args:
            celery_task_id: Celery 任务ID
            user_id: 用户ID（用于权限校验）

        Returns:
            删除的行数
        """
        rows_deleted = await asyncio.to_thread(
            self.task_history_repo.delete_task_history,
            celery_task_id,
            user_id
        )

        return rows_deleted

    async def cleanup_stale_tasks(self, user_id: int, minutes: int = 5) -> int:
        """
        清理僵尸任务（标记为失败）

        Args:
            user_id: 用户ID
            minutes: 超时分钟数

        Returns:
            清理的任务数量
        """
        count = await asyncio.to_thread(
            self.task_history_repo.cleanup_stale_tasks,
            user_id,
            minutes
        )

        logger.info(f"清理了 {count} 个僵尸任务 (user_id={user_id})")
        return count

    # ==================== 业务逻辑方法 ====================

    async def get_task_list_with_statistics(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> Dict:
        """
        获取任务列表和统计信息（组合查询）

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            status: 按状态筛选（可选）
            task_type: 按任务类型筛选（可选）

        Returns:
            包含任务列表、总数和统计信息的字典
        """
        # 并发查询任务列表和统计信息
        tasks_future = self.get_recent_history(
            user_id, limit, offset, status, task_type
        )
        stats_future = self.get_statistics(user_id)

        tasks_result, stats = await asyncio.gather(tasks_future, stats_future)
        tasks, total = tasks_result

        return {
            'tasks': tasks,
            'total': total,
            'limit': limit,
            'offset': offset,
            'statistics': stats
        }

    async def check_task_ownership(self, celery_task_id: str, user_id: int) -> bool:
        """
        检查任务是否属于指定用户

        Args:
            celery_task_id: Celery 任务ID
            user_id: 用户ID

        Returns:
            是否属于该用户
        """
        task = await asyncio.to_thread(
            self.task_history_repo.get_by_task_id,
            celery_task_id
        )

        if not task:
            return False

        return task.get('user_id') == user_id

    async def validate_and_create_or_update(
        self,
        celery_task_id: str,
        task_name: str,
        display_name: Optional[str] = None,
        task_type: str = 'other',
        user_id: Optional[int] = None,
        params: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        status: Optional[str] = None
    ) -> Dict:
        """
        验证并创建或更新任务历史记录

        如果任务已存在，则更新状态；否则创建新记录

        Args:
            celery_task_id: Celery 任务ID
            task_name: 任务名称
            display_name: 显示名称
            task_type: 任务类型
            user_id: 用户ID
            params: 任务参数
            metadata: 元数据
            status: 任务状态（可选）

        Returns:
            任务历史记录（格式化后）
        """
        # 检查是否已存在
        existing_task = await asyncio.to_thread(
            self.task_history_repo.get_by_task_id,
            celery_task_id
        )

        if existing_task:
            # 如果提供了状态，则更新
            if status:
                return await self.update_task_status(
                    celery_task_id,
                    status=status
                )
            # 否则返回现有记录
            return self.format_task_dict(existing_task)

        # 创建新记录
        task = await self.create_task_history(
            celery_task_id,
            task_name,
            display_name,
            task_type,
            user_id,
            params,
            metadata
        )

        # 如果提供了状态，立即更新
        if status and status != 'pending':
            return await self.update_task_status(
                celery_task_id,
                status=status
            )

        return task
