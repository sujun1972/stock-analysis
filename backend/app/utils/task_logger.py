"""
定时任务执行日志工具
用于记录定时任务的执行历史到数据库
"""

from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
import json


class TaskExecutionLogger:
    """任务执行日志记录器"""

    def __init__(self, db_connection):
        """
        初始化日志记录器

        Args:
            db_connection: 数据库连接对象
        """
        self.db = db_connection

    def get_task_id(self, task_name: str) -> Optional[int]:
        """
        根据任务名称获取任务ID

        Args:
            task_name: 任务名称

        Returns:
            任务ID，未找到返回None
        """
        try:
            query = "SELECT id FROM scheduled_tasks WHERE task_name = %s"
            result = self.db._execute_query(query, (task_name,))
            return result[0][0] if result else None
        except Exception as e:
            logger.error(f"获取任务ID失败: {e}")
            return None

    def log_task_start(self, task_name: str, module: str) -> Optional[int]:
        """
        记录任务开始执行

        Args:
            task_name: 任务名称
            module: 模块名称

        Returns:
            执行历史记录ID
        """
        try:
            task_id = self.get_task_id(task_name)

            insert_query = """
                INSERT INTO task_execution_history (
                    task_id,
                    task_name,
                    module,
                    status,
                    started_at
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """

            result = self.db._execute_query(
                insert_query,
                (task_id, task_name, module, 'running', datetime.now())
            )

            history_id = result[0][0] if result else None
            logger.info(f"📝 记录任务开始: {task_name} (历史ID: {history_id})")
            return history_id

        except Exception as e:
            logger.error(f"记录任务开始失败: {e}")
            return None

    def log_task_success(
        self,
        history_id: int,
        result_summary: Optional[Dict[str, Any]] = None
    ):
        """
        记录任务成功完成

        Args:
            history_id: 执行历史记录ID
            result_summary: 执行结果摘要
        """
        try:
            update_query = """
                UPDATE task_execution_history
                SET
                    status = 'success',
                    completed_at = %s,
                    duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))::INTEGER,
                    result_summary = %s::jsonb
                WHERE id = %s
            """

            now = datetime.now()
            self.db._execute_update(
                update_query,
                (now, now, json.dumps(result_summary or {}), history_id)
            )

            # 更新scheduled_tasks表的last_run_at和last_status
            self._update_task_status(history_id, 'success', None)

            logger.info(f"✅ 记录任务成功: 历史ID {history_id}")

        except Exception as e:
            logger.error(f"记录任务成功失败: {e}")

    def log_task_failure(
        self,
        history_id: int,
        error_message: str,
        result_summary: Optional[Dict[str, Any]] = None
    ):
        """
        记录任务执行失败

        Args:
            history_id: 执行历史记录ID
            error_message: 错误信息
            result_summary: 执行结果摘要
        """
        try:
            update_query = """
                UPDATE task_execution_history
                SET
                    status = 'failed',
                    completed_at = %s,
                    duration_seconds = EXTRACT(EPOCH FROM (%s - started_at))::INTEGER,
                    error_message = %s,
                    result_summary = %s::jsonb
                WHERE id = %s
            """

            now = datetime.now()
            self.db._execute_update(
                update_query,
                (now, now, error_message, json.dumps(result_summary or {}), history_id)
            )

            # 更新scheduled_tasks表的last_run_at和last_status
            self._update_task_status(history_id, 'failed', error_message)

            logger.error(f"❌ 记录任务失败: 历史ID {history_id}, 错误: {error_message}")

        except Exception as e:
            logger.error(f"记录任务失败失败: {e}")

    def _update_task_status(
        self,
        history_id: int,
        status: str,
        error_message: Optional[str]
    ):
        """
        更新scheduled_tasks表中的任务状态

        Args:
            history_id: 执行历史记录ID
            status: 任务状态
            error_message: 错误信息
        """
        try:
            # 从history表获取task_id
            query = "SELECT task_id FROM task_execution_history WHERE id = %s"
            result = self.db._execute_query(query, (history_id,))

            if not result:
                return

            task_id = result[0][0]
            if not task_id:
                return

            # 更新scheduled_tasks表
            update_query = """
                UPDATE scheduled_tasks
                SET
                    last_run_at = %s,
                    last_status = %s,
                    last_error = %s,
                    run_count = run_count + 1
                WHERE id = %s
            """

            self.db._execute_update(
                update_query,
                (datetime.now(), status, error_message, task_id)
            )

        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")


def create_task_logger():
    """
    创建任务日志记录器

    Returns:
        TaskExecutionLogger实例
    """
    from src.database.db_manager import DatabaseManager

    db = DatabaseManager()
    return TaskExecutionLogger(db)
