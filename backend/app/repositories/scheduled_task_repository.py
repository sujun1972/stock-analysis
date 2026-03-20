"""
定时任务配置 Repository

负责 scheduled_tasks 表的数据访问操作。
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class ScheduledTaskRepository(BaseRepository):
    """
    定时任务配置数据访问层

    职责:
    - 定时任务配置的 CRUD 操作
    - 任务启用/禁用管理
    - 任务执行历史更新
    - 任务分类查询
    """

    TABLE_NAME = "scheduled_tasks"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ ScheduledTaskRepository initialized")

    # ==================== 查询操作 ====================

    def get_all_tasks(self, enabled_only: bool = False) -> List[Dict]:
        """
        获取所有定时任务

        Args:
            enabled_only: 是否只返回启用的任务

        Returns:
            任务配置列表

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> tasks = repo.get_all_tasks(enabled_only=True)
            >>> len(tasks)  # 15
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
        """

        if enabled_only:
            query += " WHERE enabled = true"

        query += " ORDER BY display_order ASC, id ASC"

        try:
            result = self.execute_query(query)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询所有定时任务失败: {e}")
            raise QueryError(
                "查询定时任务失败",
                error_code="SCHEDULED_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_task_name(self, task_name: str) -> Optional[Dict]:
        """
        根据任务名称查询配置

        Args:
            task_name: 任务名称（唯一标识）

        Returns:
            任务配置字典，不存在则返回 None

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> task = repo.get_by_task_name('daily_sentiment_sync')
            >>> print(task['display_name'])  # '每日市场情绪抓取'
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
            WHERE task_name = %s
        """

        try:
            result = self.execute_query(query, (task_name,))
            if not result:
                return None

            return self._row_to_dict(result[0])

        except Exception as e:
            logger.error(f"查询任务配置失败 (task_name={task_name}): {e}")
            raise QueryError(
                "查询任务配置失败",
                error_code="TASK_CONFIG_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_id(self, task_id: int) -> Optional[Dict]:
        """
        根据任务ID查询配置

        Args:
            task_id: 任务ID

        Returns:
            任务配置字典，不存在则返回 None

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> task = repo.get_by_id(1)
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
            WHERE id = %s
        """

        try:
            result = self.execute_query(query, (task_id,))
            if not result:
                return None

            return self._row_to_dict(result[0])

        except Exception as e:
            logger.error(f"查询任务配置失败 (id={task_id}): {e}")
            raise QueryError(
                "查询任务配置失败",
                error_code="TASK_CONFIG_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_module(self, module: str) -> List[Dict]:
        """
        根据模块名称查询任务

        Args:
            module: 模块名称（如 'sentiment', 'daily', 'moneyflow'）

        Returns:
            任务配置列表

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> tasks = repo.get_by_module('sentiment')
            >>> len(tasks)  # 2
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
            WHERE module = %s
            ORDER BY display_order ASC, id ASC
        """

        try:
            result = self.execute_query(query, (module,))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询模块任务失败 (module={module}): {e}")
            raise QueryError(
                "查询模块任务失败",
                error_code="MODULE_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_category(self, category: str, enabled_only: bool = False) -> List[Dict]:
        """
        根据分类查询任务

        Args:
            category: 分类名称（如 '基础数据', '行情数据', '扩展数据'）
            enabled_only: 是否只返回启用的任务

        Returns:
            任务配置列表

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> tasks = repo.get_by_category('基础数据', enabled_only=True)
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
            WHERE category = %s
        """

        if enabled_only:
            query += " AND enabled = true"

        query += " ORDER BY display_order ASC, id ASC"

        try:
            result = self.execute_query(query, (category,))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询分类任务失败 (category={category}): {e}")
            raise QueryError(
                "查询分类任务失败",
                error_code="CATEGORY_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    def get_enabled_tasks(self) -> List[Dict]:
        """
        获取所有启用的定时任务（用于调度器加载）

        Returns:
            启用的任务配置列��

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> enabled_tasks = repo.get_enabled_tasks()
        """
        return self.get_all_tasks(enabled_only=True)

    def get_tasks_due_for_run(self, current_time: datetime) -> List[Dict]:
        """
        获取到期需要执行的任务

        Args:
            current_time: 当前时间

        Returns:
            到期的任务列表

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> from datetime import datetime
            >>> tasks = repo.get_tasks_due_for_run(datetime.now())
        """
        query = f"""
            SELECT id, task_name, module, description, cron_expression, enabled,
                   params, last_run_at, next_run_at, last_status, last_error,
                   run_count, created_by, updated_at, created_at,
                   display_name, category, display_order, points_consumption
            FROM {self.TABLE_NAME}
            WHERE enabled = true
              AND (next_run_at IS NULL OR next_run_at <= %s)
            ORDER BY next_run_at ASC
        """

        try:
            result = self.execute_query(query, (current_time,))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询到期任务失败: {e}")
            raise QueryError(
                "查询到期任务失败",
                error_code="DUE_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def create_task(
        self,
        task_name: str,
        module: str,
        description: Optional[str] = None,
        cron_expression: Optional[str] = None,
        enabled: bool = False,
        params: Optional[Dict] = None,
        display_name: Optional[str] = None,
        category: Optional[str] = None,
        display_order: Optional[int] = None,
        points_consumption: Optional[int] = None,
        created_by: str = 'system'
    ) -> Dict:
        """
        创建定时任务配置

        Args:
            task_name: 任务名称（唯一标识）
            module: 模块名称
            description: 任务描述
            cron_expression: Cron 表达式
            enabled: 是否启用
            params: 任务参数
            display_name: 显示名称
            category: 分类
            display_order: 显示排序
            points_consumption: 积分消耗
            created_by: 创建者

        Returns:
            创建的任务配置

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> task = repo.create_task(
            ...     task_name='test_task',
            ...     module='test',
            ...     description='测试任务',
            ...     cron_expression='0 9 * * *',
            ...     enabled=True
            ... )
        """
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (task_name, module, description, cron_expression, enabled, params,
             display_name, category, display_order, points_consumption, created_by,
             created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """

        params_json = json.dumps(params) if params else None

        try:
            result = self.execute_query(
                query,
                (
                    task_name,
                    module,
                    description,
                    cron_expression,
                    enabled,
                    params_json,
                    display_name,
                    category,
                    display_order,
                    points_consumption,
                    created_by
                )
            )

            new_id = result[0][0] if result else None
            logger.info(f"创建定时任务: {task_name} (id={new_id})")

            return self.get_by_id(new_id)

        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            raise DatabaseError(
                "创建定时任务失败",
                error_code="TASK_CREATE_FAILED",
                reason=str(e)
            )

    def update_task_config(
        self,
        task_name: str,
        cron_expression: Optional[str] = None,
        enabled: Optional[bool] = None,
        params: Optional[Dict] = None,
        description: Optional[str] = None,
        display_name: Optional[str] = None,
        category: Optional[str] = None,
        display_order: Optional[int] = None,
        points_consumption: Optional[int] = None
    ) -> int:
        """
        更新任务配置

        Args:
            task_name: 任务名称
            cron_expression: Cron 表达式
            enabled: 是否启用
            params: 任务参数
            description: 任务描述
            display_name: 显示名称
            category: 分类
            display_order: 显示排序
            points_consumption: 积分消耗

        Returns:
            影响的行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> repo.update_task_config(
            ...     task_name='daily_sentiment_sync',
            ...     cron_expression='0 10 * * *',
            ...     enabled=True
            ... )
        """
        update_fields = []
        update_params = []

        if cron_expression is not None:
            update_fields.append("cron_expression = %s")
            update_params.append(cron_expression)

        if enabled is not None:
            update_fields.append("enabled = %s")
            update_params.append(enabled)

        if params is not None:
            update_fields.append("params = %s::jsonb")
            update_params.append(json.dumps(params))

        if description is not None:
            update_fields.append("description = %s")
            update_params.append(description)

        if display_name is not None:
            update_fields.append("display_name = %s")
            update_params.append(display_name)

        if category is not None:
            update_fields.append("category = %s")
            update_params.append(category)

        if display_order is not None:
            update_fields.append("display_order = %s")
            update_params.append(display_order)

        if points_consumption is not None:
            update_fields.append("points_consumption = %s")
            update_params.append(points_consumption)

        if not update_fields:
            logger.warning(f"更新任务配置时没有提供任何字段: {task_name}")
            return 0

        update_fields.append("updated_at = NOW()")
        update_params.append(task_name)

        query = f"""
            UPDATE {self.TABLE_NAME}
            SET {', '.join(update_fields)}
            WHERE task_name = %s
        """

        try:
            rows_affected = self.execute_update(query, tuple(update_params))
            logger.info(f"更新任务配置: {task_name}")
            return rows_affected

        except Exception as e:
            logger.error(f"更新任务配置失败: {e}")
            raise DatabaseError(
                "更新任务配置失败",
                error_code="TASK_UPDATE_FAILED",
                reason=str(e)
            )

    def toggle_task(self, task_name: str, enabled: bool) -> int:
        """
        启用/禁用任务

        Args:
            task_name: 任务名称
            enabled: 是否启用

        Returns:
            影响的行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> repo.toggle_task('daily_sentiment_sync', enabled=False)
        """
        return self.update_task_config(task_name, enabled=enabled)

    def update_last_run(
        self,
        task_name: str,
        status: str,
        error: Optional[str] = None,
        next_run_at: Optional[datetime] = None
    ) -> int:
        """
        更新任务最后运行状态

        Args:
            task_name: 任务名称
            status: 运行状态（'success', 'failed'）
            error: 错误信息（可选）
            next_run_at: 下次运行时间（可选）

        Returns:
            影响的行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> repo.update_last_run(
            ...     task_name='daily_sentiment_sync',
            ...     status='success'
            ... )
        """
        update_fields = [
            "last_run_at = NOW()",
            "last_status = %s",
            "run_count = run_count + 1",
            "updated_at = NOW()"
        ]
        update_params = [status]

        if error is not None:
            update_fields.append("last_error = %s")
            update_params.append(error)
        else:
            update_fields.append("last_error = NULL")

        if next_run_at is not None:
            update_fields.append("next_run_at = %s")
            update_params.append(next_run_at)

        update_params.append(task_name)

        query = f"""
            UPDATE {self.TABLE_NAME}
            SET {', '.join(update_fields)}
            WHERE task_name = %s
        """

        try:
            rows_affected = self.execute_update(query, tuple(update_params))
            logger.debug(f"更新任务运行状态: {task_name} - {status}")
            return rows_affected

        except Exception as e:
            logger.error(f"更新任务运行状态失败: {e}")
            raise DatabaseError(
                "更新任务运行状态失败",
                error_code="TASK_RUN_UPDATE_FAILED",
                reason=str(e)
            )

    def update_next_run_time(self, task_name: str, next_run_at: datetime) -> int:
        """
        更新任务下次运行时间

        Args:
            task_name: 任务名称
            next_run_at: 下次运行时间

        Returns:
            影响的行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> from datetime import datetime, timedelta
            >>> next_time = datetime.now() + timedelta(days=1)
            >>> repo.update_next_run_time('daily_sentiment_sync', next_time)
        """
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET next_run_at = %s,
                updated_at = NOW()
            WHERE task_name = %s
        """

        try:
            rows_affected = self.execute_update(query, (next_run_at, task_name))
            return rows_affected

        except Exception as e:
            logger.error(f"更新下次运行时间失败: {e}")
            raise DatabaseError(
                "更新下次运行时间失败",
                error_code="NEXT_RUN_UPDATE_FAILED",
                reason=str(e)
            )

    def delete_task(self, task_name: str) -> int:
        """
        删除定时任务

        Args:
            task_name: 任务名称

        Returns:
            删除的行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> repo.delete_task('test_task')
        """
        query = f"DELETE FROM {self.TABLE_NAME} WHERE task_name = %s"

        try:
            rows_affected = self.execute_update(query, (task_name,))
            logger.info(f"删除定时任务: {task_name}")
            return rows_affected

        except Exception as e:
            logger.error(f"删除定时任务失败: {e}")
            raise DatabaseError(
                "删除定时任务失败",
                error_code="TASK_DELETE_FAILED",
                reason=str(e)
            )

    # ==================== 批量操作 ====================

    def bulk_update_metadata(self, tasks_metadata: List[Dict]) -> int:
        """
        批量更新任务元数据（display_name, category, display_order, points_consumption）

        Args:
            tasks_metadata: 任务元数据列表，每项包含 task_name 和要更新的字段

        Returns:
            更新的总行数

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> metadata = [
            ...     {
            ...         'task_name': 'daily_stock_list_sync',
            ...         'display_name': '每日股票列表',
            ...         'category': '基础数据',
            ...         'display_order': 100,
            ...         'points_consumption': 2000
            ...     }
            ... ]
            >>> repo.bulk_update_metadata(metadata)
        """
        total_updated = 0

        for task_meta in tasks_metadata:
            task_name = task_meta.get('task_name')
            if not task_name:
                logger.warning("跳过无 task_name 的元数据项")
                continue

            # 构建更新字段
            update_kwargs = {}
            for key in ['display_name', 'category', 'display_order', 'points_consumption']:
                if key in task_meta:
                    update_kwargs[key] = task_meta[key]

            if not update_kwargs:
                continue

            try:
                rows = self.update_task_config(task_name, **update_kwargs)
                total_updated += rows
            except Exception as e:
                logger.error(f"批量更新任务元数据失败 ({task_name}): {e}")
                continue

        logger.info(f"批量更新任务元数据完成，共更新 {total_updated} 个任务")
        return total_updated

    # ==================== 统计查询 ====================

    def get_statistics(self) -> Dict:
        """
        获取任务统计信息

        Returns:
            统计信息字典

        Examples:
            >>> repo = ScheduledTaskRepository()
            >>> stats = repo.get_statistics()
            >>> print(stats['total_tasks'])  # 37
            >>> print(stats['enabled_tasks'])  # 15
        """
        query = f"""
            SELECT
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN enabled THEN 1 END) as enabled_tasks,
                COUNT(CASE WHEN NOT enabled THEN 1 END) as disabled_tasks,
                COUNT(CASE WHEN last_status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN last_status = 'failed' THEN 1 END) as failed_count,
                COUNT(DISTINCT category) as category_count,
                COUNT(DISTINCT module) as module_count,
                SUM(run_count) as total_runs
            FROM {self.TABLE_NAME}
        """

        try:
            result = self.execute_query(query)
            if not result:
                return self._empty_statistics()

            row = result[0]
            return {
                "total_tasks": row[0] or 0,
                "enabled_tasks": row[1] or 0,
                "disabled_tasks": row[2] or 0,
                "success_count": row[3] or 0,
                "failed_count": row[4] or 0,
                "category_count": row[5] or 0,
                "module_count": row[6] or 0,
                "total_runs": row[7] or 0
            }

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            raise QueryError(
                "获取任务统计失败",
                error_code="TASK_STATISTICS_QUERY_FAILED",
                reason=str(e)
            )

    # ==================== 辅助方法 ====================

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将数据库行转换为字典

        列顺序：id, task_name, module, description, cron_expression, enabled,
               params, last_run_at, next_run_at, last_status, last_error,
               run_count, created_by, updated_at, created_at,
               display_name, category, display_order, points_consumption
        """
        return {
            "id": row[0],
            "task_name": row[1],
            "module": row[2],
            "description": row[3],
            "cron_expression": row[4],
            "enabled": row[5],
            "params": row[6],
            "last_run_at": row[7],
            "next_run_at": row[8],
            "last_status": row[9],
            "last_error": row[10],
            "run_count": row[11],
            "created_by": row[12],
            "updated_at": row[13],
            "created_at": row[14],
            "display_name": row[15],
            "category": row[16],
            "display_order": row[17],
            "points_consumption": row[18]
        }

    def _empty_statistics(self) -> Dict:
        """返回空统计信息"""
        return {
            "total_tasks": 0,
            "enabled_tasks": 0,
            "disabled_tasks": 0,
            "success_count": 0,
            "failed_count": 0,
            "category_count": 0,
            "module_count": 0,
            "total_runs": 0
        }
