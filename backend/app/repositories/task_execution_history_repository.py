"""
Task Execution History Repository
定时任务执行历史数据访问层
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class TaskExecutionHistoryRepository(BaseRepository):
    """
    定时任务执行历史 Repository

    管理 task_execution_history 表的数据访问操作

    主要功能：
    - 记录定时任务执行历史
    - 查询任务执行历史记录
    - 统计任务执行成功率
    - 获取最近执行状态
    - 清理过期历史记录

    注意：
    - task_execution_history 表记录定时任务的执行历史（Celery Beat 调度）
    - celery_task_history 表记录所有 Celery 任务历史（包括手动触发）
    - 两者是不同的历史记录系统
    """

    TABLE_NAME = "task_execution_history"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ TaskExecutionHistoryRepository initialized")

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'id': row[0],
            'task_id': row[1],
            'task_name': row[2],
            'module': row[3],
            'status': row[4],
            'started_at': row[5],
            'completed_at': row[6],
            'duration_seconds': row[7],
            'result_summary': row[8],
            'error_message': row[9],
            'sync_log_id': row[10]
        }

    # ==================== 创建操作 ====================

    def create(self, execution_data: Dict) -> int:
        """
        创建任务执行历史记录

        Args:
            execution_data: 执行记录数据
                - task_id: 任务配置ID（scheduled_tasks.id）
                - task_name: 任务名称
                - module: 模块名称
                - status: 执行状态（pending/running/success/failed）
                - started_at: 开始时间（可选）
                - result_summary: 结果摘要（JSON，可选）
                - error_message: 错误信息（可选）
                - sync_log_id: 同步日志ID（可选）

        Returns:
            新记录的ID

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> record_id = repo.create({
            ...     'task_id': 1,
            ...     'task_name': 'daily_stock_sync',
            ...     'module': 'stock_data',
            ...     'status': 'running',
            ...     'started_at': datetime.now()
            ... })
        """
        try:
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    task_id, task_name, module, status, started_at,
                    result_summary, error_message, sync_log_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            params = (
                execution_data.get('task_id'),
                execution_data.get('task_name'),
                execution_data.get('module'),
                execution_data.get('status', 'pending'),
                execution_data.get('started_at') or datetime.now(),
                execution_data.get('result_summary'),
                execution_data.get('error_message'),
                execution_data.get('sync_log_id')
            )

            result = self.execute_query(query, params)
            record_id = result[0][0] if result else None  # RETURNING id 返回第一列

            if record_id:
                logger.debug(f"创建任务执行记录: id={record_id}, task_name={execution_data.get('task_name')}")
            else:
                raise DatabaseError(
                    "创建任务执行记录失败：未返回ID",
                    error_code="CREATE_EXECUTION_NO_ID"
                )

            return record_id

        except Exception as e:
            logger.error(f"创建任务执行记录失败: {e}")
            raise DatabaseError(
                "创建任务执行记录失败",
                error_code="CREATE_EXECUTION_FAILED",
                reason=str(e)
            )

    # ==================== 更新操作 ====================

    def update_status(
        self,
        execution_id: int,
        status: str,
        completed_at: Optional[datetime] = None,
        duration_seconds: Optional[int] = None,
        result_summary: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> int:
        """
        更新任务执行状态

        Args:
            execution_id: 执行记录ID
            status: 新状态（success/failed）
            completed_at: 完成时间（可选，默认当前时间）
            duration_seconds: 执行时长（秒）
            result_summary: 结果摘要（JSON）
            error_message: 错误信息

        Returns:
            受影响的行数

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> repo.update_status(
            ...     execution_id=1,
            ...     status='success',
            ...     duration_seconds=120,
            ...     result_summary={'records': 1000}
            ... )
        """
        try:
            query = f"""
                UPDATE {self.TABLE_NAME}
                SET
                    status = %s,
                    completed_at = %s,
                    duration_seconds = %s,
                    result_summary = %s,
                    error_message = %s
                WHERE id = %s
            """
            params = (
                status,
                completed_at or datetime.now(),
                duration_seconds,
                result_summary,
                error_message,
                execution_id
            )

            affected_rows = self.execute_update(query, params)
            logger.debug(f"更新任务执行状态: id={execution_id}, status={status}")
            return affected_rows

        except Exception as e:
            logger.error(f"更新任务执行状态失败: id={execution_id}, error={e}")
            raise DatabaseError(
                "更新任务执行状态失败",
                error_code="UPDATE_EXECUTION_STATUS_FAILED",
                execution_id=execution_id,
                reason=str(e)
            )

    # ==================== 查询操作 ====================

    def get_by_id(self, execution_id: int) -> Optional[Dict]:
        """
        按ID查询执行记录

        Args:
            execution_id: 执行记录ID

        Returns:
            执行记录字典，不存在则返回 None

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> record = repo.get_by_id(1)
            >>> print(record['status'])
        """
        try:
            query = f"""
                SELECT id, task_id, task_name, module, status, started_at,
                       completed_at, duration_seconds, result_summary,
                       error_message, sync_log_id
                FROM {self.TABLE_NAME} WHERE id = %s
            """
            result = self.execute_query(query, (execution_id,))
            return self._row_to_dict(result[0]) if result else None

        except Exception as e:
            logger.error(f"查询执行记录失败: id={execution_id}, error={e}")
            raise QueryError(
                "查询执行记录失败",
                error_code="EXECUTION_QUERY_FAILED",
                execution_id=execution_id,
                reason=str(e)
            )

    def get_by_task_id(
        self,
        task_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        按任务配置ID查询执行历史

        Args:
            task_id: 任务配置ID（scheduled_tasks.id）
            limit: 限制数量
            offset: 偏移量

        Returns:
            执行记录列表（按开始时间倒序）

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> records = repo.get_by_task_id(task_id=1, limit=20)
            >>> print(f"最近20次执行记录: {len(records)}")
        """
        try:
            query = f"""
                SELECT id, task_id, task_name, module, status, started_at,
                       completed_at, duration_seconds, result_summary,
                       error_message, sync_log_id
                FROM {self.TABLE_NAME}
                WHERE task_id = %s
                ORDER BY started_at DESC
                LIMIT %s OFFSET %s
            """
            result = self.execute_query(query, (task_id, limit, offset))
            logger.debug(f"查询到 {len(result)} 条任务执行记录: task_id={task_id}")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询任务执行历史失败: task_id={task_id}, error={e}")
            raise QueryError(
                "查询任务执行历史失败",
                error_code="TASK_HISTORY_QUERY_FAILED",
                task_id=task_id,
                reason=str(e)
            )

    def get_by_task_name(
        self,
        task_name: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        按任务名称查询执行历史

        Args:
            task_name: 任务名称
            limit: 限制数量
            offset: 偏移量

        Returns:
            执行记录列表（按开始时间倒序）

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> records = repo.get_by_task_name('daily_stock_sync', limit=10)
        """
        try:
            query = f"""
                SELECT id, task_id, task_name, module, status, started_at,
                       completed_at, duration_seconds, result_summary,
                       error_message, sync_log_id
                FROM {self.TABLE_NAME}
                WHERE task_name = %s
                ORDER BY started_at DESC
                LIMIT %s OFFSET %s
            """
            result = self.execute_query(query, (task_name, limit, offset))
            logger.debug(f"查询到 {len(result)} 条执行记录: task_name={task_name}")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询执行历史失败: task_name={task_name}, error={e}")
            raise QueryError(
                "查询执行历史失败",
                error_code="TASK_NAME_HISTORY_QUERY_FAILED",
                task_name=task_name,
                reason=str(e)
            )

    def get_recent_executions(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的执行记录

        Args:
            limit: 限制数量
            status: 状态过滤（可选）

        Returns:
            执行记录列表（按开始时间倒序）

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> recent = repo.get_recent_executions(limit=50, status='failed')
            >>> print(f"最近失败的任务: {len(recent)}")
        """
        try:
            base_query = f"""
                SELECT id, task_id, task_name, module, status, started_at,
                       completed_at, duration_seconds, result_summary,
                       error_message, sync_log_id
                FROM {self.TABLE_NAME}
            """

            if status:
                query = base_query + " WHERE status = %s ORDER BY started_at DESC LIMIT %s"
                params = (status, limit)
            else:
                query = base_query + " ORDER BY started_at DESC LIMIT %s"
                params = (limit,)

            result = self.execute_query(query, params)
            logger.debug(f"查询到 {len(result)} 条最近执行记录")
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询最近执行记录失败: {e}")
            raise QueryError(
                "查询最近执行记录失败",
                error_code="RECENT_EXECUTIONS_QUERY_FAILED",
                reason=str(e)
            )

    def get_latest_by_task_id(self, task_id: int) -> Optional[Dict]:
        """
        获取任务的最新执行记录

        Args:
            task_id: 任务配置ID

        Returns:
            最新执行记录，不存在则返回 None

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> latest = repo.get_latest_by_task_id(1)
            >>> if latest:
            ...     print(f"最后执行状态: {latest['status']}")
        """
        try:
            query = f"""
                SELECT id, task_id, task_name, module, status, started_at,
                       completed_at, duration_seconds, result_summary,
                       error_message, sync_log_id
                FROM {self.TABLE_NAME}
                WHERE task_id = %s
                ORDER BY started_at DESC
                LIMIT 1
            """
            result = self.execute_query(query, (task_id,))
            return self._row_to_dict(result[0]) if result else None

        except Exception as e:
            logger.error(f"查询最新执行记录失败: task_id={task_id}, error={e}")
            raise QueryError(
                "查询最新执行记录失败",
                error_code="LATEST_EXECUTION_QUERY_FAILED",
                task_id=task_id,
                reason=str(e)
            )

    # ==================== 统计操作 ====================

    def get_statistics_by_task_id(
        self,
        task_id: int,
        days: int = 30
    ) -> Dict:
        """
        获取任务执行统计（最近N天）

        Args:
            task_id: 任务配置ID
            days: 统计天数

        Returns:
            统计信息字典：
                - total_executions: 总执行次数
                - success_count: 成功次数
                - failed_count: 失败次数
                - success_rate: 成功率
                - avg_duration: 平均耗时（秒）

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> stats = repo.get_statistics_by_task_id(task_id=1, days=7)
            >>> print(f"近7天成功率: {stats['success_rate']:.1%}")
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                    AVG(duration_seconds) as avg_duration
                FROM {self.TABLE_NAME}
                WHERE task_id = %s
                    AND started_at >= NOW() - INTERVAL '%s days'
            """
            result = self.execute_query(query, (task_id, days))

            if result and result[0][0] > 0:  # result[0][0] 是 total_executions
                row = result[0]
                total = row[0]  # total_executions
                success = row[1] or 0  # success_count
                failed = row[2] or 0  # failed_count
                avg_duration = row[3]  # avg_duration
                success_rate = (success / total) if total > 0 else 0.0

                return {
                    'total_executions': total,
                    'success_count': success,
                    'failed_count': failed,
                    'success_rate': success_rate,
                    'avg_duration': float(avg_duration) if avg_duration else 0.0
                }
            else:
                return {
                    'total_executions': 0,
                    'success_count': 0,
                    'failed_count': 0,
                    'success_rate': 0.0,
                    'avg_duration': 0.0
                }

        except Exception as e:
            logger.error(f"统计任务执行情况失败: task_id={task_id}, error={e}")
            raise QueryError(
                "统计任务执行情况失败",
                error_code="TASK_STATISTICS_FAILED",
                task_id=task_id,
                reason=str(e)
            )

    def count_by_task_id(self, task_id: int) -> int:
        """
        统计任务执行次数

        Args:
            task_id: 任务配置ID

        Returns:
            执行次数

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> count = repo.count_by_task_id(1)
            >>> print(f"任务总执行次数: {count}")
        """
        try:
            query = f"""
                SELECT COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE task_id = %s
            """
            result = self.execute_query(query, (task_id,))
            count = result[0][0] if result else 0  # result[0][0] 表示第一行第一列
            return count

        except Exception as e:
            logger.error(f"统计任务执行次数失败: task_id={task_id}, error={e}")
            raise QueryError(
                "统计任务执行次数失败",
                error_code="TASK_COUNT_FAILED",
                task_id=task_id,
                reason=str(e)
            )

    # ==================== 删除操作 ====================

    def delete_by_task_id(self, task_id: int) -> int:
        """
        删除任务的所有执行历史

        Args:
            task_id: 任务配置ID

        Returns:
            删除的记录数

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> deleted = repo.delete_by_task_id(1)
            >>> print(f"已删除 {deleted} 条执行记录")
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE task_id = %s"
            affected_rows = self.execute_update(query, (task_id,))
            logger.debug(f"删除任务执行历史: task_id={task_id}, count={affected_rows}")
            return affected_rows

        except Exception as e:
            logger.error(f"删除执行历史失败: task_id={task_id}, error={e}")
            raise DatabaseError(
                "删除执行历史失败",
                error_code="DELETE_EXECUTION_HISTORY_FAILED",
                task_id=task_id,
                reason=str(e)
            )

    def delete_old_records(self, days: int = 90) -> int:
        """
        清理过期执行记录（保留最近N天）

        Args:
            days: 保留天数

        Returns:
            删除的记录数

        Examples:
            >>> repo = TaskExecutionHistoryRepository()
            >>> deleted = repo.delete_old_records(days=90)
            >>> print(f"清理了 {deleted} 条90天前的执行记录")
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE started_at < NOW() - INTERVAL '%s days'
            """
            affected_rows = self.execute_update(query, (days,))
            logger.info(f"清理过期执行记录: days={days}, deleted={affected_rows}")
            return affected_rows

        except Exception as e:
            logger.error(f"清理过期记录失败: days={days}, error={e}")
            raise DatabaseError(
                "清理过期记录失败",
                error_code="DELETE_OLD_RECORDS_FAILED",
                days=days,
                reason=str(e)
            )
