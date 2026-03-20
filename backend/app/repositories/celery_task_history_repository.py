"""
Celery 任务历史 Repository

负责 celery_task_history 表的数据访问操作。
"""

from typing import Dict, List, Optional
from datetime import datetime
import json
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class CeleryTaskHistoryRepository(BaseRepository):
    """
    Celery 任务历史数据访问层

    职责:
    - 任务历史记录的 CRUD 操作
    - 任务状态查询和更新
    - 任务统计和清理
    """

    TABLE_NAME = "celery_task_history"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CeleryTaskHistoryRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_task_id(self, celery_task_id: str) -> Optional[Dict]:
        """
        根据 Celery 任务ID查询任务历史

        Args:
            celery_task_id: Celery 任务ID (UUID格式)

        Returns:
            任务历史记录字典，不存在则返回 None

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> task = repo.get_by_task_id('a1b2c3d4-...')
            >>> print(task['status'])  # 'success'
        """
        query = f"""
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM {self.TABLE_NAME}
            WHERE celery_task_id = %s
        """
        try:
            result = self.execute_query(query, (celery_task_id,))
            if not result:
                return None

            row = result[0]
            return self._row_to_dict(row)

        except Exception as e:
            logger.error(f"查询任务历史失败 (task_id={celery_task_id}): {e}")
            raise QueryError(
                "查询任务历史失败",
                error_code="CELERY_TASK_QUERY_FAILED",
                reason=str(e)
            )

    def get_active_tasks(self, user_id: Optional[int] = None) -> List[Dict]:
        """
        获取活跃任务（pending, running, progress 状态）

        Args:
            user_id: 用户ID（可选，不传则返回所有用户的活跃任务）

        Returns:
            活跃任务列表

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> active_tasks = repo.get_active_tasks(user_id=1)
            >>> len(active_tasks)  # 5
        """
        query = f"""
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM {self.TABLE_NAME}
            WHERE status IN ('pending', 'running', 'progress')
        """
        params = []

        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)

        query += " ORDER BY created_at DESC"

        try:
            result = self.execute_query(query, tuple(params) if params else None)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询活跃任务失败: {e}")
            raise QueryError(
                "查询活跃任务失败",
                error_code="ACTIVE_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    def get_recent_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        task_type: Optional[str] = None
    ) -> tuple[List[Dict], int]:
        """
        获取最近任务历史（带分页和筛选）

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            status: 按状态筛选（可选）
            task_type: 按任务类型筛选（可选）

        Returns:
            (任务列表, 总数) 元组

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> tasks, total = repo.get_recent_history(user_id=1, limit=20)
            >>> print(f"共 {total} 条记录，返回 {len(tasks)} 条")
        """
        # 构建查询条件
        where_clauses = ["user_id = %s"]
        query_params = [user_id]

        if status:
            where_clauses.append("status = %s")
            query_params.append(status)

        if task_type:
            where_clauses.append("task_type = %s")
            query_params.append(task_type)

        where_sql = " AND ".join(where_clauses)

        # 查询总数
        count_query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            WHERE {where_sql}
        """
        try:
            count_result = self.execute_query(count_query, tuple(query_params))
            total = count_result[0][0] if count_result else 0

            # 查询数据
            query_params.extend([limit, offset])
            select_query = f"""
                SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                       status, progress, created_at, started_at, completed_at, duration_ms,
                       result, error, worker, params, metadata
                FROM {self.TABLE_NAME}
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """

            result = self.execute_query(select_query, tuple(query_params))
            tasks = [self._row_to_dict(row) for row in result]

            return tasks, total

        except Exception as e:
            logger.error(f"查询任务历史列表失败: {e}")
            raise QueryError(
                "查询任务历史列表失败",
                error_code="TASK_HISTORY_LIST_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
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

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> stats = repo.get_statistics(user_id=1)
            >>> print(stats['total_tasks'])  # 150
            >>> print(stats['success_rate'])  # 95.5
        """
        where_clauses = []
        query_params = []

        if user_id is not None:
            where_clauses.append("user_id = %s")
            query_params.append(user_id)

        if start_date:
            where_clauses.append("created_at >= %s::date")
            query_params.append(start_date)

        if end_date:
            where_clauses.append("created_at <= %s::date + interval '1 day'")
            query_params.append(end_date)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        query = f"""
            SELECT
                COUNT(*) as total_tasks,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count,
                COUNT(CASE WHEN status = 'failure' THEN 1 END) as failure_count,
                COUNT(CASE WHEN status IN ('pending', 'running', 'progress') THEN 1 END) as active_count,
                AVG(CASE WHEN duration_ms IS NOT NULL THEN duration_ms END) as avg_duration_ms,
                MAX(duration_ms) as max_duration_ms,
                MIN(CASE WHEN duration_ms > 0 THEN duration_ms END) as min_duration_ms,
                COUNT(DISTINCT task_type) as task_type_count
            FROM {self.TABLE_NAME}
            WHERE {where_sql}
        """

        try:
            result = self.execute_query(
                query,
                tuple(query_params) if query_params else None
            )

            if not result:
                return self._empty_statistics()

            row = result[0]
            total = row[0] or 0
            success = row[1] or 0

            return {
                "total_tasks": total,
                "success_count": success,
                "failure_count": row[2] or 0,
                "active_count": row[3] or 0,
                "success_rate": round((success / total * 100), 2) if total > 0 else 0.0,
                "avg_duration_ms": int(row[4]) if row[4] else None,
                "max_duration_ms": row[5],
                "min_duration_ms": row[6],
                "task_type_count": row[7] or 0
            }

        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            raise QueryError(
                "获取任务统计失败",
                error_code="TASK_STATISTICS_QUERY_FAILED",
                reason=str(e)
            )

    def get_stale_tasks(self, user_id: int, minutes: int = 5) -> List[Dict]:
        """
        获取僵尸任务（运行中但超过指定时间未完成）

        Args:
            user_id: 用户ID
            minutes: 超时分钟数

        Returns:
            僵尸任务列表

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> stale_tasks = repo.get_stale_tasks(user_id=1, minutes=5)
        """
        query = f"""
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM {self.TABLE_NAME}
            WHERE user_id = %s
              AND status IN ('running', 'pending', 'progress')
              AND created_at < NOW() - INTERVAL '%s minutes'
            ORDER BY created_at ASC
        """

        try:
            result = self.execute_query(query, (user_id, minutes))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询僵尸任务失败: {e}")
            raise QueryError(
                "查询僵尸任务失败",
                error_code="STALE_TASKS_QUERY_FAILED",
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def create_task_history(
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
            创建的任务历史记录

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> task = repo.create_task_history(
            ...     celery_task_id='a1b2c3d4',
            ...     task_name='tasks.sync_data',
            ...     display_name='数据同步',
            ...     task_type='data_sync',
            ...     user_id=1
            ... )
        """
        # 先检查是否已存在
        existing = self.get_by_task_id(celery_task_id)
        if existing:
            logger.info(f"任务历史记录已存在: {celery_task_id}")
            return existing

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s)
            RETURNING id
        """

        params_json = json.dumps(params) if params else None
        metadata_json = json.dumps(metadata) if metadata else None
        created_at = datetime.now()

        try:
            result = self.execute_query(
                query,
                (
                    celery_task_id,
                    task_name,
                    display_name,
                    task_type,
                    user_id,
                    params_json,
                    metadata_json,
                    created_at
                )
            )

            new_id = result[0][0] if result else None

            logger.info(f"创建任务历史记录: {celery_task_id} - {display_name}")

            # 返回完整记录
            return self.get_by_task_id(celery_task_id)

        except Exception as e:
            logger.error(f"创建任务历史记录失败: {e}")
            raise DatabaseError(
                "创建任务历史记录失败",
                error_code="TASK_HISTORY_CREATE_FAILED",
                reason=str(e)
            )

    def update_task_status(
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
    ) -> int:
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
            影响的行数

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> repo.update_task_status(
            ...     celery_task_id='a1b2c3d4',
            ...     status='running',
            ...     progress=50
            ... )
        """
        # 构建更新语句
        update_fields = []
        update_params = []

        if status is not None:
            update_fields.append("status = %s")
            update_params.append(status)

        if progress is not None:
            update_fields.append("progress = %s")
            update_params.append(progress)

        if started_at is not None:
            update_fields.append("started_at = %s")
            update_params.append(started_at)

        if completed_at is not None:
            update_fields.append("completed_at = %s")
            update_params.append(completed_at)

            # 自动计算耗时（如果有started_at且未提供duration_ms）
            if duration_ms is None and started_at is not None:
                duration = int((completed_at - started_at).total_seconds() * 1000)
                update_fields.append("duration_ms = %s")
                update_params.append(duration)

        if duration_ms is not None:
            update_fields.append("duration_ms = %s")
            update_params.append(duration_ms)

        if result is not None:
            update_fields.append("result = %s::jsonb")
            update_params.append(json.dumps(result))

        if error is not None:
            update_fields.append("error = %s")
            update_params.append(error)

        if worker is not None:
            update_fields.append("worker = %s")
            update_params.append(worker)

        if not update_fields:
            logger.warning(f"更新任务状态时没有提供任何字段: {celery_task_id}")
            return 0

        # 执行更新
        update_params.append(celery_task_id)
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET {', '.join(update_fields)}
            WHERE celery_task_id = %s
        """

        try:
            rows_affected = self.execute_update(query, tuple(update_params))
            logger.debug(f"更新任务状态: {celery_task_id} - status={status}")
            return rows_affected

        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            raise DatabaseError(
                "更新任务状态失败",
                error_code="TASK_STATUS_UPDATE_FAILED",
                reason=str(e)
            )

    def delete_task_history(self, celery_task_id: str, user_id: Optional[int] = None) -> int:
        """
        删除任务历史记录

        Args:
            celery_task_id: Celery 任务ID
            user_id: 用户ID（可选，用于权限校验）

        Returns:
            删除的行数

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> repo.delete_task_history('a1b2c3d4', user_id=1)
        """
        query = f"DELETE FROM {self.TABLE_NAME} WHERE celery_task_id = %s"
        params = [celery_task_id]

        if user_id is not None:
            query += " AND user_id = %s"
            params.append(user_id)

        try:
            rows_affected = self.execute_update(query, tuple(params))
            logger.info(f"删除任务历史记录: {celery_task_id}")
            return rows_affected

        except Exception as e:
            logger.error(f"删除任务历史记录失败: {e}")
            raise DatabaseError(
                "删除任务历史记录失败",
                error_code="TASK_HISTORY_DELETE_FAILED",
                reason=str(e)
            )

    def cleanup_stale_tasks(self, user_id: int, minutes: int = 5) -> int:
        """
        清理僵尸任务（标记为失败）

        Args:
            user_id: 用户ID
            minutes: 超时分钟数

        Returns:
            清理的任务数量

        Examples:
            >>> repo = CeleryTaskHistoryRepository()
            >>> count = repo.cleanup_stale_tasks(user_id=1, minutes=5)
            >>> print(f"清理了 {count} 个僵尸任务")
        """
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET status = 'failure',
                completed_at = NOW(),
                error = 'Task marked as stale and cleaned up',
                duration_ms = CASE
                    WHEN started_at IS NOT NULL THEN
                        EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                    ELSE
                        EXTRACT(EPOCH FROM (NOW() - created_at)) * 1000
                END
            WHERE user_id = %s
              AND status IN ('running', 'pending', 'progress')
              AND created_at < NOW() - INTERVAL '%s minutes'
        """

        try:
            rows_affected = self.execute_update(query, (user_id, minutes))
            logger.info(f"清理了 {rows_affected} 个僵尸任务 (user_id={user_id})")
            return rows_affected

        except Exception as e:
            logger.error(f"清理僵尸任务失败: {e}")
            raise DatabaseError(
                "清理僵尸任务失败",
                error_code="STALE_TASKS_CLEANUP_FAILED",
                reason=str(e)
            )

    # ==================== 辅助方法 ====================

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将数据库行转换为字典

        列顺序：id, celery_task_id, task_name, display_name, task_type, user_id,
               status, progress, created_at, started_at, completed_at, duration_ms,
               result, error, worker, params, metadata
        """
        return {
            "id": row[0],
            "celery_task_id": row[1],
            "task_name": row[2],
            "display_name": row[3],
            "task_type": row[4],
            "user_id": row[5],
            "status": row[6],
            "progress": row[7],
            "created_at": row[8],
            "started_at": row[9],
            "completed_at": row[10],
            "duration_ms": row[11],
            "result": row[12],
            "error": row[13],
            "worker": row[14],
            "params": row[15],
            "metadata": row[16]
        }

    def _empty_statistics(self) -> Dict:
        """返回空统计信息"""
        return {
            "total_tasks": 0,
            "success_count": 0,
            "failure_count": 0,
            "active_count": 0,
            "success_rate": 0.0,
            "avg_duration_ms": None,
            "max_duration_ms": None,
            "min_duration_ms": None,
            "task_type_count": 0
        }
