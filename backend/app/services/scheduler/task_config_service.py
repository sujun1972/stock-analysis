"""
定时任务配置管理服务

职责：
- 任务配置的 CRUD 操作
- 任务启用/禁用
- 任务配置验证
"""

import asyncio
from typing import Any, Dict, List, Optional
from loguru import logger

from app.repositories import ScheduledTaskRepository
from app.core.exceptions import QueryError, DatabaseError, ValidationError
from .cron_service import CronService


class TaskConfigService:
    """
    定时任务配置管理服务

    职责：
    - 任务配置的增删改查
    - 任务启用/禁用
    - 任务元数据管理
    """

    # 分类排序配置
    CATEGORY_ORDER = {
        '基础数据': 1,
        '行情数据': 2,
        '扩展数据': 3,
        '资金流向': 4,
        '两融及转融通': 5,
        '市场情绪': 6,
        '盘前分析': 7,
        '质量监控': 8,
        '报告通知': 9,
        '系统维护': 10
    }

    def __init__(self):
        self.scheduled_task_repo = ScheduledTaskRepository()
        self.cron_service = CronService()
        logger.debug("✓ TaskConfigService initialized")

    # ==================== 查询操作 ====================

    async def get_all_tasks(self) -> List[Dict]:
        """
        获取所有定时任务列表（按分类和显示顺序排序）

        Returns:
            任务配置列表

        Examples:
            >>> service = TaskConfigService()
            >>> tasks = await service.get_all_tasks()
            >>> len(tasks)  # 37
        """
        try:
            tasks = await asyncio.to_thread(self.scheduled_task_repo.get_all_tasks)

            # 排序任务
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    self.CATEGORY_ORDER.get(t.get('category'), 99),
                    t.get('display_order', 999),
                    t.get('id', 0)
                )
            )

            # 格式化时间字段
            for task in sorted_tasks:
                task['last_run_at'] = self.cron_service.format_datetime(task.get('last_run_at'))
                task['next_run_at'] = self.cron_service.format_datetime(task.get('next_run_at'))
                task['created_at'] = self.cron_service.format_datetime(task.get('created_at'))
                task['updated_at'] = self.cron_service.format_datetime(task.get('updated_at'))

            return sorted_tasks

        except Exception as e:
            logger.error(f"获取定时任务列表失败: {e}")
            raise QueryError(
                "获取定时任务列表失败",
                error_code="GET_TASKS_FAILED",
                reason=str(e)
            )

    async def get_task_by_id(self, task_id: int) -> Dict:
        """
        根据任务 ID 获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务配置字典

        Raises:
            QueryError: 任务不存在

        Examples:
            >>> service = TaskConfigService()
            >>> task = await service.get_task_by_id(1)
        """
        try:
            task = await asyncio.to_thread(self.scheduled_task_repo.get_by_id, task_id)

            if not task:
                raise QueryError(
                    f"任务 {task_id} 不存在",
                    error_code="TASK_NOT_FOUND",
                    reason=f"Task ID {task_id} not found in database"
                )

            # 格式化时间字段
            task['last_run_at'] = self.cron_service.format_datetime(task.get('last_run_at'))
            task['next_run_at'] = self.cron_service.format_datetime(task.get('next_run_at'))
            task['created_at'] = self.cron_service.format_datetime(task.get('created_at'))
            task['updated_at'] = self.cron_service.format_datetime(task.get('updated_at'))

            return task

        except QueryError:
            raise
        except Exception as e:
            logger.error(f"获取任务详情失败 (id={task_id}): {e}")
            raise QueryError(
                "获取任务详情失败",
                error_code="GET_TASK_FAILED",
                reason=str(e)
            )

    # ==================== 创建操作 ====================

    async def create_task(
        self,
        task_name: str,
        module: str,
        description: Optional[str] = None,
        cron_expression: str = "0 0 * * *",
        enabled: bool = False,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """
        创建定时任务

        Args:
            task_name: 任务名称（唯一标识）
            module: 模块名称
            description: 任务描述
            cron_expression: Cron 表达式
            enabled: 是否启用
            params: 任务参数

        Returns:
            创建的任务配置

        Raises:
            ValidationError: 参数验证失败
            DatabaseError: 数据库操作失败

        Examples:
            >>> service = TaskConfigService()
            >>> task = await service.create_task(
            ...     task_name='test_task',
            ...     module='test',
            ...     cron_expression='0 9 * * *'
            ... )
        """
        try:
            # 验证 Cron 表达式
            if not self.cron_service.validate_cron_expression(cron_expression):
                raise ValidationError(
                    '无效的Cron表达式，格式应为: "分 时 日 月 周"',
                    error_code="INVALID_CRON",
                    reason=f"Invalid cron expression: {cron_expression}"
                )

            # 检查任务名称是否已存在
            existing_task = await asyncio.to_thread(
                self.scheduled_task_repo.get_by_task_name,
                task_name
            )
            if existing_task:
                raise ValidationError(
                    f"任务名称 '{task_name}' 已存在",
                    error_code="TASK_NAME_EXISTS",
                    reason=f"Task name '{task_name}' already exists"
                )

            # 计算下次执行时间
            next_run_at = self.cron_service.calculate_next_run_time(cron_expression)

            # 创建任务
            task = await asyncio.to_thread(
                self.scheduled_task_repo.create_task,
                task_name=task_name,
                module=module,
                description=description,
                cron_expression=cron_expression,
                enabled=enabled,
                params=params or {}
            )

            # 如果计算出了下次执行时间，更新它
            if next_run_at:
                await asyncio.to_thread(
                    self.scheduled_task_repo.update_next_run_time,
                    task_name,
                    next_run_at
                )
                task['next_run_at'] = next_run_at

            logger.info(f"✓ 创建定时任务: {task_name} (ID: {task['id']})")

            # 格式化时间字段
            task['last_run_at'] = self.cron_service.format_datetime(task.get('last_run_at'))
            task['next_run_at'] = self.cron_service.format_datetime(task.get('next_run_at'))
            task['created_at'] = self.cron_service.format_datetime(task.get('created_at'))
            task['updated_at'] = self.cron_service.format_datetime(task.get('updated_at'))

            return task

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            raise DatabaseError(
                "创建定时任务失���",
                error_code="CREATE_TASK_FAILED",
                reason=str(e)
            )

    # ==================== 更新操作 ====================

    async def update_task(
        self,
        task_id: int,
        description: Optional[str] = None,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None,
        params: Optional[Dict[str, Any]] = None,
        display_name: Optional[str] = None,
        category: Optional[str] = None,
        display_order: Optional[int] = None,
        points_consumption: Optional[int] = None
    ) -> Dict:
        """
        更新定时任务配置

        Args:
            task_id: 任务ID
            description: 任务描述
            cron_expression: Cron 表达式
            enabled: 是否启用
            params: 任务参数
            display_name: 显示名称
            category: 分类
            display_order: 显示排序
            points_consumption: 积分消耗

        Returns:
            更新后的任务配置

        Raises:
            ValidationError: 参数验证失败
            QueryError: 任务不存在
            DatabaseError: 数据库操作失败

        Examples:
            >>> service = TaskConfigService()
            >>> task = await service.update_task(
            ...     task_id=1,
            ...     cron_expression='0 10 * * *',
            ...     enabled=True
            ... )
        """
        try:
            # 获取现有任务
            task = await asyncio.to_thread(self.scheduled_task_repo.get_by_id, task_id)
            if not task:
                raise QueryError(
                    f"任务 {task_id} 不存在",
                    error_code="TASK_NOT_FOUND",
                    reason=f"Task ID {task_id} not found"
                )

            # 验证 Cron 表达式
            if cron_expression is not None and not self.cron_service.validate_cron_expression(cron_expression):
                raise ValidationError(
                    '无效的Cron表达式，格式应为: "分 时 日 月 周"',
                    error_code="INVALID_CRON",
                    reason=f"Invalid cron expression: {cron_expression}"
                )

            # 验证显示顺序
            if display_order is not None and display_order < 0:
                raise ValidationError(
                    '显示顺序必须大于等于0',
                    error_code="INVALID_DISPLAY_ORDER",
                    reason=f"Display order must be >= 0: {display_order}"
                )

            # 验证积分消耗
            if points_consumption is not None and points_consumption < 0:
                raise ValidationError(
                    '积分消耗必须大于等于0',
                    error_code="INVALID_POINTS",
                    reason=f"Points consumption must be >= 0: {points_consumption}"
                )

            # 准备更新参数
            update_kwargs = {}
            if description is not None:
                update_kwargs['description'] = description
            if enabled is not None:
                update_kwargs['enabled'] = enabled
            if params is not None:
                update_kwargs['params'] = params
            if display_name is not None:
                update_kwargs['display_name'] = display_name
            if category is not None:
                update_kwargs['category'] = category
            if display_order is not None:
                update_kwargs['display_order'] = display_order
            if points_consumption is not None:
                update_kwargs['points_consumption'] = points_consumption

            # 如果更新了 Cron 表达式，同时更新下次执行时间
            if cron_expression is not None:
                update_kwargs['cron_expression'] = cron_expression
                next_run_at = self.cron_service.calculate_next_run_time(cron_expression)
                if next_run_at:
                    await asyncio.to_thread(
                        self.scheduled_task_repo.update_next_run_time,
                        task['task_name'],
                        next_run_at
                    )

            if not update_kwargs:
                raise ValidationError(
                    "没有需要更新的字段",
                    error_code="NO_UPDATE_FIELDS",
                    reason="No fields to update"
                )

            # 执行更新
            await asyncio.to_thread(
                self.scheduled_task_repo.update_task_config,
                task['task_name'],
                **update_kwargs
            )

            logger.info(f"✓ 更新定时任务: {task_id}")

            # 返回更新后的任务
            return await self.get_task_by_id(task_id)

        except (ValidationError, QueryError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"更新定时任务失败: {e}")
            raise DatabaseError(
                "更新定时任务失败",
                error_code="UPDATE_TASK_FAILED",
                reason=str(e)
            )

    async def toggle_task(self, task_id: int) -> Dict:
        """
        切换任务启用状态

        Args:
            task_id: 任务ID

        Returns:
            更新后的任务配置（包含新的 enabled 状态）

        Raises:
            QueryError: 任务不存在
            DatabaseError: 数据库操作失败

        Examples:
            >>> service = TaskConfigService()
            >>> task = await service.toggle_task(1)
            >>> print(task['enabled'])  # True 或 False
        """
        try:
            # 获取当前任务
            task = await asyncio.to_thread(self.scheduled_task_repo.get_by_id, task_id)
            if not task:
                raise QueryError(
                    f"任务 {task_id} 不存在",
                    error_code="TASK_NOT_FOUND",
                    reason=f"Task ID {task_id} not found"
                )

            # 切换状态
            new_enabled = not task['enabled']
            await asyncio.to_thread(
                self.scheduled_task_repo.toggle_task,
                task['task_name'],
                new_enabled
            )

            logger.info(f"✓ 切换定时任务状态: {task_id} -> {new_enabled}")

            # 返回更新后的任务
            return await self.get_task_by_id(task_id)

        except QueryError:
            raise
        except Exception as e:
            logger.error(f"切换任务状态失败: {e}")
            raise DatabaseError(
                "切换任务状态失败",
                error_code="TOGGLE_TASK_FAILED",
                reason=str(e)
            )

    # ==================== 删除操作 ====================

    async def delete_task(self, task_id: int) -> int:
        """
        删除定时任务

        Args:
            task_id: 任务ID

        Returns:
            删除的行数

        Raises:
            QueryError: 任务不存在
            DatabaseError: 数据库操作失败

        Examples:
            >>> service = TaskConfigService()
            >>> count = await service.delete_task(1)
            >>> print(count)  # 1
        """
        try:
            # 获取任务信息
            task = await asyncio.to_thread(self.scheduled_task_repo.get_by_id, task_id)
            if not task:
                raise QueryError(
                    f"任务 {task_id} 不存在",
                    error_code="TASK_NOT_FOUND",
                    reason=f"Task ID {task_id} not found"
                )

            # 删除任务
            count = await asyncio.to_thread(
                self.scheduled_task_repo.delete_task,
                task['task_name']
            )

            logger.info(f"✓ 删除定时任��: {task_id}")
            return count

        except QueryError:
            raise
        except Exception as e:
            logger.error(f"删除定时任务失败: {e}")
            raise DatabaseError(
                "删除定时任务失败",
                error_code="DELETE_TASK_FAILED",
                reason=str(e)
            )
