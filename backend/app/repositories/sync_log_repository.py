"""
同步日志 Repository
管理 sync_log 表的数据访问

表结构：sync_log
- id: 自增主键
- task_id: 任务ID
- task_type: 任务类型（manual, scheduled）
- data_type: 数据类型（stock_list, daily, minute, realtime）
- data_source: 数据源
- status: 状态（running, completed, failed）
- total_count: 总数
- success_count: 成功数
- failed_count: 失败数
- progress: 进度
- error_message: 错误信息
- started_at: 开始时间
- completed_at: 完成时间
- duration_seconds: 持续时间（秒）
"""

from typing import Dict, List, Optional

from loguru import logger

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class SyncLogRepository(BaseRepository):
    """
    同步日志 Repository

    职责：
    - sync_log 表的 CRUD 操作
    - 任务状态查询
    - 任务历史记录
    """

    TABLE_NAME = "sync_log"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ SyncLogRepository initialized")

    # ==================== 查询操作 ====================

    def get_latest_by_module(self, module: str) -> Optional[Dict]:
        """
        获取特定模块的最新同步记录

        Args:
            module: 模块名称（stock_list, daily, minute, realtime）

        Returns:
            最新同步记录，不存在则返回 None

        Examples:
            >>> repo = SyncLogRepository()
            >>> record = repo.get_latest_by_module('stock_list')
            >>> if record:
            ...     print(f"状态: {record['status']}")
        """
        try:
            query = f"""
                SELECT
                    id, task_id, task_type, data_type, data_source, status,
                    total_count, success_count, failed_count, progress,
                    error_message, started_at, completed_at, duration_seconds
                FROM {self.TABLE_NAME}
                WHERE data_type = %s
                ORDER BY started_at DESC
                LIMIT 1
            """

            result = self.execute_query(query, (module,))

            if not result:
                return None

            row = result[0]
            return {
                "id": row[0],
                "task_id": row[1],
                "task_type": row[2],
                "data_type": row[3],
                "data_source": row[4],
                "status": row[5],
                "total_count": row[6],
                "success_count": row[7],
                "failed_count": row[8],
                "progress": row[9],
                "error_message": row[10],
                "started_at": row[11].strftime("%Y-%m-%d %H:%M:%S") if row[11] else "",
                "completed_at": row[12].strftime("%Y-%m-%d %H:%M:%S") if row[12] else "",
                "duration_seconds": row[13],
            }

        except Exception as e:
            logger.error(f"查询模块同步记录失败 (module={module}): {e}")
            raise QueryError(
                f"模块同步记录查询失败: {module}",
                error_code="SYNC_LOG_QUERY_FAILED",
                module=module,
                reason=str(e),
            )

    def get_by_task_id(self, task_id: str) -> Optional[Dict]:
        """
        根据任务ID查询同步记录

        Args:
            task_id: 任务ID

        Returns:
            同步记录，不存在则返回 None

        Examples:
            >>> repo = SyncLogRepository()
            >>> record = repo.get_by_task_id('task-123')
            >>> if record:
            ...     print(f"进度: {record['progress']}%")
        """
        try:
            query = f"""
                SELECT
                    id, task_id, task_type, data_type, data_source, status,
                    total_count, success_count, failed_count, progress,
                    error_message, started_at, completed_at, duration_seconds
                FROM {self.TABLE_NAME}
                WHERE task_id = %s
            """

            result = self.execute_query(query, (task_id,))

            if not result:
                return None

            row = result[0]
            return {
                "id": row[0],
                "task_id": row[1],
                "task_type": row[2],
                "data_type": row[3],
                "data_source": row[4],
                "status": row[5],
                "total_count": row[6],
                "success_count": row[7],
                "failed_count": row[8],
                "progress": row[9],
                "error_message": row[10],
                "started_at": row[11].isoformat() if row[11] else None,
                "completed_at": row[12].isoformat() if row[12] else None,
                "duration_seconds": row[13],
            }

        except Exception as e:
            logger.error(f"查询任务同步记录失败 (task_id={task_id}): {e}")
            raise QueryError(
                "任务同步记录查询失败",
                error_code="SYNC_LOG_QUERY_FAILED",
                task_id=task_id,
                reason=str(e),
            )

    def get_recent_logs(self, limit: int = 10, data_type: Optional[str] = None) -> List[Dict]:
        """
        获取最近的同步日志

        Args:
            limit: 返回数量
            data_type: 数据类型筛选（可选）

        Returns:
            同步日志列表

        Examples:
            >>> repo = SyncLogRepository()
            >>> logs = repo.get_recent_logs(limit=5, data_type='daily')
            >>> for log in logs:
            ...     print(f"{log['task_id']}: {log['status']}")
        """
        try:
            if data_type:
                query = f"""
                    SELECT
                        id, task_id, task_type, data_type, data_source, status,
                        total_count, success_count, failed_count, progress,
                        error_message, started_at, completed_at, duration_seconds
                    FROM {self.TABLE_NAME}
                    WHERE data_type = %s
                    ORDER BY started_at DESC
                    LIMIT %s
                """
                params = (data_type, limit)
            else:
                query = f"""
                    SELECT
                        id, task_id, task_type, data_type, data_source, status,
                        total_count, success_count, failed_count, progress,
                        error_message, started_at, completed_at, duration_seconds
                    FROM {self.TABLE_NAME}
                    ORDER BY started_at DESC
                    LIMIT %s
                """
                params = (limit,)

            result = self.execute_query(query, params)

            logs = []
            for row in result:
                logs.append({
                    "id": row[0],
                    "task_id": row[1],
                    "task_type": row[2],
                    "data_type": row[3],
                    "data_source": row[4],
                    "status": row[5],
                    "total_count": row[6],
                    "success_count": row[7],
                    "failed_count": row[8],
                    "progress": row[9],
                    "error_message": row[10],
                    "started_at": row[11].isoformat() if row[11] else None,
                    "completed_at": row[12].isoformat() if row[12] else None,
                    "duration_seconds": row[13],
                })

            return logs

        except Exception as e:
            logger.error(f"查询最近同步日志失败: {e}")
            raise QueryError(
                "最近同步日志查询失败",
                error_code="SYNC_LOG_LIST_FAILED",
                reason=str(e),
            )

    # ==================== 写入操作 ====================

    def create_task(self, task_id: str, module: str, data_source: str, task_type: str = "manual") -> int:
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
            task_type: 任务类型（manual, scheduled）

        Returns:
            插入的记录ID

        Examples:
            >>> repo = SyncLogRepository()
            >>> record_id = repo.create_task('task-123', 'stock_list', 'tushare')
            >>> print(f"创建任务记录ID: {record_id}")
        """
        try:
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    task_id, task_type, data_type, data_source, status
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """

            result = self.execute_query(query, (task_id, task_type, module, data_source, "running"))

            if not result:
                raise DatabaseError(
                    "创建同步任务失败：未返回ID",
                    error_code="SYNC_LOG_CREATE_NO_ID",
                    task_id=task_id,
                )

            record_id = result[0][0]
            logger.info(f"✓ 创建同步任务: {task_id} ({module}) -> ID={record_id}")
            return record_id

        except Exception as e:
            logger.error(f"创建同步任务失败 (task_id={task_id}): {e}")
            raise DatabaseError(
                "同步任务创建失败",
                error_code="SYNC_LOG_CREATE_FAILED",
                task_id=task_id,
                module=module,
                reason=str(e),
            )

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """
        更新同步任务状态

        Args:
            task_id: 任务ID
            status: 状态（可选）
            total_count: 总数（可选）
            success_count: 成功数（可选）
            failed_count: 失败数（可选）
            progress: 进度（可选）
            error_message: 错误信息（可选）

        Returns:
            影响的行数

        Examples:
            >>> repo = SyncLogRepository()
            >>> rows = repo.update_task('task-123', status='completed', progress=100)
            >>> print(f"更新了 {rows} 条记录")
        """
        try:
            # 构建动态更新语句
            updates = []
            params = []

            if status is not None:
                updates.append("status = %s")
                params.append(status)

            if total_count is not None:
                updates.append("total_count = %s")
                params.append(total_count)

            if success_count is not None:
                updates.append("success_count = %s")
                params.append(success_count)

            if failed_count is not None:
                updates.append("failed_count = %s")
                params.append(failed_count)

            if progress is not None:
                updates.append("progress = %s")
                params.append(progress)

            if error_message is not None:
                updates.append("error_message = %s")
                params.append(error_message)

            # 如果状态是完成或失败，设置完成时间和持续时间
            if status in ["completed", "failed"]:
                updates.append("completed_at = CURRENT_TIMESTAMP")
                updates.append(
                    "duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))::INTEGER"
                )

            if not updates:
                return 0

            query = f"""
                UPDATE {self.TABLE_NAME}
                SET {', '.join(updates)}
                WHERE task_id = %s
            """
            params.append(task_id)

            affected_rows = self.execute_update(query, tuple(params))
            logger.debug(f"✓ 更新同步任务: {task_id} (affected={affected_rows})")
            return affected_rows

        except Exception as e:
            logger.error(f"更新同步任务失败 (task_id={task_id}): {e}")
            raise DatabaseError(
                "同步任务更新失败",
                error_code="SYNC_LOG_UPDATE_FAILED",
                task_id=task_id,
                reason=str(e),
            )

    def delete_old_logs(self, days: int = 30) -> int:
        """
        删除旧的同步日志

        Args:
            days: 保留天数（删除超过该天数的记录）

        Returns:
            删除的记录数

        Examples:
            >>> repo = SyncLogRepository()
            >>> deleted = repo.delete_old_logs(days=30)
            >>> print(f"删除了 {deleted} 条旧日志")
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE started_at < NOW() - INTERVAL '%s days'
            """

            affected_rows = self.execute_update(query, (days,))
            logger.info(f"✓ 删除了 {affected_rows} 条旧同步日志 (>{days}天)")
            return affected_rows

        except Exception as e:
            logger.error(f"删除旧同步日志失败: {e}")
            raise DatabaseError(
                "删除旧同步日志失败",
                error_code="SYNC_LOG_DELETE_OLD_FAILED",
                days=days,
                reason=str(e),
            )

    # ==================== 统计操作 ====================

    def get_statistics(self, data_type: Optional[str] = None, days: int = 7) -> Dict:
        """
        获取同步统计信息

        Args:
            data_type: 数据类型筛选（可选）
            days: 统计天数

        Returns:
            统计信息字典

        Examples:
            >>> repo = SyncLogRepository()
            >>> stats = repo.get_statistics(data_type='daily', days=7)
            >>> print(f"成功率: {stats['success_rate']}%")
        """
        try:
            if data_type:
                query = f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                        AVG(duration_seconds) as avg_duration,
                        MAX(duration_seconds) as max_duration,
                        MIN(duration_seconds) as min_duration
                    FROM {self.TABLE_NAME}
                    WHERE data_type = %s
                    AND started_at >= NOW() - INTERVAL '%s days'
                """
                params = (data_type, days)
            else:
                query = f"""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                        AVG(duration_seconds) as avg_duration,
                        MAX(duration_seconds) as max_duration,
                        MIN(duration_seconds) as min_duration
                    FROM {self.TABLE_NAME}
                    WHERE started_at >= NOW() - INTERVAL '%s days'
                """
                params = (days,)

            result = self.execute_query(query, params)

            if not result:
                return {
                    "total": 0,
                    "completed": 0,
                    "failed": 0,
                    "running": 0,
                    "success_rate": 0.0,
                    "avg_duration": 0.0,
                    "max_duration": 0,
                    "min_duration": 0,
                }

            row = result[0]
            total = row[0] or 0
            completed = row[1] or 0
            failed = row[2] or 0
            running = row[3] or 0
            avg_duration = float(row[4]) if row[4] else 0.0
            max_duration = row[5] or 0
            min_duration = row[6] or 0

            success_rate = (completed / total * 100) if total > 0 else 0.0

            return {
                "total": total,
                "completed": completed,
                "failed": failed,
                "running": running,
                "success_rate": round(success_rate, 2),
                "avg_duration": round(avg_duration, 2),
                "max_duration": max_duration,
                "min_duration": min_duration,
            }

        except Exception as e:
            logger.error(f"获取同步统计信息失败: {e}")
            raise QueryError(
                "同步统计信息查询失败",
                error_code="SYNC_LOG_STATS_FAILED",
                reason=str(e),
            )
