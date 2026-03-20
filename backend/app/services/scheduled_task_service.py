"""
定时任务管理服务（已废弃）

⚠️ DEPRECATED: 此文件已废弃，请使用模块化的新架构

新架构位置：app.services.scheduler
- CronService: Cron 表达式工具
- TaskConfigService: 任务配置管理（CRUD）
- TaskHistoryService: 任务执行历史查询
- TaskExecutionService: 任务执行和状态查询
- ScheduledTaskService: 统一服务（向后兼容）

迁移示例：
    # 旧代码
    from app.services.scheduled_task_service import ScheduledTaskService

    # 新代码（推荐）
    from app.services.scheduler import TaskConfigService, CronService

    # 新代码（向后兼容）
    from app.services.scheduler import ScheduledTaskService

计划移除时间：2026年9月

---

原有文档（已过时）：

负责定时任务配置的业务逻辑，包括：
- 任务配置的 CRUD 操作
- Cron 表达式验证和解析
- 任务执行状态管理
- 任务执行历史查询
"""

import warnings

# 显示废弃警告
warnings.warn(
    "scheduled_task_service.py 已废弃，请使用 app.services.scheduler 模块。"
    "详见文件顶部的迁移指南。",
    DeprecationWarning,
    stacklevel=2
)

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.repositories import ScheduledTaskRepository
from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository
from app.repositories.task_execution_history_repository import TaskExecutionHistoryRepository
from app.core.exceptions import QueryError, DatabaseError, ValidationError


class ScheduledTaskService:
    """
    定时任务管理服务

    职责：
    - 任务配置的增删改查
    - Cron 表达式验证和下次执行时间计算
    - 任务执行状态更新
    - 任务执行历史查询
    - 业务逻辑编排（如任务启用/禁用、手动执行等）
    """

    def __init__(self):
        self.scheduled_task_repo = ScheduledTaskRepository()
        self.celery_task_repo = CeleryTaskHistoryRepository()
        self.execution_history_repo = TaskExecutionHistoryRepository()
        logger.debug("✓ ScheduledTaskService initialized")

    # ==================== Cron 工具方法 ====================

    @staticmethod
    def validate_cron_expression(cron_expr: str) -> bool:
        """
        验证 Cron 表达式是否有效

        Args:
            cron_expr: Cron 表达式，格式: "分 时 日 月 周"

        Returns:
            是否有效

        Examples:
            >>> service = ScheduledTaskService()
            >>> service.validate_cron_expression("0 9 * * *")  # True
            >>> service.validate_cron_expression("invalid")    # False
        """
        try:
            from croniter import croniter
            croniter(cron_expr, datetime.now())
            return True
        except Exception:
            # croniter 不可用或表达式无效，使用简单验证
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                return False
            # 简单检查每个字段是否符合基本格式
            return all(part for part in parts)

    @staticmethod
    def calculate_next_run_time(cron_expr: str) -> Optional[datetime]:
        """
        计算下次执行时间

        Args:
            cron_expr: Cron 表达式

        Returns:
            下次执行时间，解析失败返回 None

        Examples:
            >>> service = ScheduledTaskService()
            >>> next_time = service.calculate_next_run_time("0 9 * * *")
            >>> print(next_time)  # 下一个9:00
        """
        try:
            from croniter import croniter
            cron = croniter(cron_expr, datetime.now())
            return cron.get_next(datetime)
        except Exception:
            return None

    # ==================== 查询操作 ====================

    async def get_all_tasks(self) -> List[Dict]:
        """
        获取所有定时任务列表（按分类和显示顺序排序）

        Returns:
            任务配置列表

        Examples:
            >>> service = ScheduledTaskService()
            >>> tasks = await service.get_all_tasks()
            >>> len(tasks)  # 37
        """
        try:
            tasks = await asyncio.to_thread(self.scheduled_task_repo.get_all_tasks)

            # 自定义分类排序
            category_order = {
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

            # 排序任务
            sorted_tasks = sorted(
                tasks,
                key=lambda t: (
                    category_order.get(t.get('category'), 99),
                    t.get('display_order', 999),
                    t.get('id', 0)
                )
            )

            # 格式化时间字段
            for task in sorted_tasks:
                task['last_run_at'] = self._format_datetime(task.get('last_run_at'))
                task['next_run_at'] = self._format_datetime(task.get('next_run_at'))
                task['created_at'] = self._format_datetime(task.get('created_at'))
                task['updated_at'] = self._format_datetime(task.get('updated_at'))

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
            >>> service = ScheduledTaskService()
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
            task['last_run_at'] = self._format_datetime(task.get('last_run_at'))
            task['next_run_at'] = self._format_datetime(task.get('next_run_at'))
            task['created_at'] = self._format_datetime(task.get('created_at'))
            task['updated_at'] = self._format_datetime(task.get('updated_at'))

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
            >>> service = ScheduledTaskService()
            >>> task = await service.create_task(
            ...     task_name='test_task',
            ...     module='test',
            ...     cron_expression='0 9 * * *'
            ... )
        """
        try:
            # 验证模块名称
            valid_modules = [
                "stock_list", "new_stocks", "delisted_stocks",
                "daily", "minute", "realtime"
            ]
            if module not in valid_modules:
                raise ValidationError(
                    f"无效的模块名称，支持: {', '.join(valid_modules)}",
                    error_code="INVALID_MODULE",
                    reason=f"Module '{module}' not in valid modules"
                )

            # 验证 Cron 表达式
            if not self.validate_cron_expression(cron_expression):
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
            next_run_at = self.calculate_next_run_time(cron_expression)

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
            task['last_run_at'] = self._format_datetime(task.get('last_run_at'))
            task['next_run_at'] = self._format_datetime(task.get('next_run_at'))
            task['created_at'] = self._format_datetime(task.get('created_at'))
            task['updated_at'] = self._format_datetime(task.get('updated_at'))

            return task

        except (ValidationError, DatabaseError):
            raise
        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            raise DatabaseError(
                "创建定时任务失败",
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
            >>> service = ScheduledTaskService()
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
            if cron_expression is not None and not self.validate_cron_expression(cron_expression):
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
                next_run_at = self.calculate_next_run_time(cron_expression)
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
            >>> service = ScheduledTaskService()
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
            >>> service = ScheduledTaskService()
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

            logger.info(f"✓ 删除定时任务: {task_id}")
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

    # ==================== 任务执行历史 ====================

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
            >>> service = ScheduledTaskService()
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
                    "started_at": self._format_datetime(record.get('started_at')),
                    "completed_at": self._format_datetime(record.get('completed_at')),
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
            >>> service = ScheduledTaskService()
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
                    "started_at": self._format_datetime(record.get('started_at')),
                    "completed_at": self._format_datetime(record.get('completed_at')),
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

    # ==================== 任务执行 ====================

    async def execute_task_async(
        self,
        task_id: int,
        user_id: int
    ) -> Dict:
        """
        手动执行定时任务（异步提交到 Celery）

        Note:
            此方法需要同时写入 task_execution_history 和 celery_task_history 两个表
            暂时使用 DatabaseManager，待创建相应 Repository 后重构

        Args:
            task_id: 任务ID
            user_id: 执行用户ID

        Returns:
            执行结果字典，包含 celery_task_id

        Raises:
            QueryError: 任务不存在
            DatabaseError: 执行失败

        Examples:
            >>> service = ScheduledTaskService()
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
            enabled = task_config.get('enabled', True)

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

            import json
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
            >>> service = ScheduledTaskService()
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
                "started_at": self._format_datetime(record.get('started_at')),
                "completed_at": self._format_datetime(record.get('completed_at')),
                "result": record.get('result_summary'),
                "error": record.get('error_message')
            }

        except Exception as e:
            logger.error(f"获取任务执行状态失败: {e}")
            raise QueryError(
                "获取任务执行状态失败",
                error_code="GET_STATUS_FAILED",
                reason=str(e)
            )

    # ==================== Cron 验证 ====================

    async def validate_and_get_next_run(self, cron_expression: str) -> Dict:
        """
        验证 Cron 表达式并返回下次执行时间

        Args:
            cron_expression: Cron 表达式

        Returns:
            验证结果字典

        Examples:
            >>> service = ScheduledTaskService()
            >>> result = await service.validate_and_get_next_run("0 9 * * *")
            >>> print(result['valid'])  # True
            >>> print(result['next_run_at'])  # "2026-03-21 09:00:00"
        """
        is_valid = self.validate_cron_expression(cron_expression)

        if not is_valid:
            return {
                "valid": False,
                "error": "格式应为: 分 时 日 月 周 (例: 0 9 * * 1-5)"
            }

        next_run = self.calculate_next_run_time(cron_expression)

        return {
            "valid": True,
            "next_run_at": self._format_datetime(next_run) if next_run else None,
            "cron_expression": cron_expression
        }

    # ==================== 辅助方法 ====================

    @staticmethod
    def _format_datetime(dt: Optional[datetime]) -> Optional[str]:
        """
        格式化 datetime 为字符串

        Args:
            dt: datetime 对象

        Returns:
            格式化后的字符串 (YYYY-MM-DD HH:MM:SS)，None 则返回 None
        """
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d %H:%M:%S")
