"""
下载状态管理器

管理数据下载的断点续传功能，支持：
- 保存和加载下载检查点
- 跟踪下载进度
- 恢复中断的下载任务
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass, asdict
from src.database.db_manager import DatabaseManager, get_database
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DownloadCheckpoint:
    """下载检查点数据类"""

    task_id: str
    data_type: str
    start_date: date
    end_date: date
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    last_completed_date: Optional[date] = None
    completed_symbols: Optional[List[str]] = None
    progress_percent: float = 0.0
    total_items: int = 0
    completed_items: int = 0
    status: str = 'running'  # running, paused, completed, failed
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换日期为字符串
        if isinstance(data['start_date'], date):
            data['start_date'] = data['start_date'].isoformat()
        if isinstance(data['end_date'], date):
            data['end_date'] = data['end_date'].isoformat()
        if isinstance(data['last_completed_date'], date):
            data['last_completed_date'] = data['last_completed_date'].isoformat()
        # 转换列表为JSON字符串
        if data['symbols']:
            data['symbols'] = json.dumps(data['symbols'])
        if data['completed_symbols']:
            data['completed_symbols'] = json.dumps(data['completed_symbols'])
        return data


class DownloadStateManager:
    """
    下载状态管理器

    功能：
    - 保存下载检查点
    - 加载下载检查点
    - 更新下载进度
    - 清理过期检查点
    - 记录下载日志
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化下载状态管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager if db_manager else get_database()

    def save_checkpoint(self, checkpoint: DownloadCheckpoint) -> bool:
        """
        保存下载检查点

        Args:
            checkpoint: 检查点数据

        Returns:
            是否保存成功
        """
        try:
            data = checkpoint.to_dict()

            # 构建SQL
            sql = """
                INSERT INTO download_checkpoints (
                    task_id, data_type, symbol, symbols, start_date, end_date,
                    last_completed_date, completed_symbols, progress_percent,
                    total_items, completed_items, status, error_message, retry_count
                ) VALUES (
                    %(task_id)s, %(data_type)s, %(symbol)s, %(symbols)s, %(start_date)s, %(end_date)s,
                    %(last_completed_date)s, %(completed_symbols)s, %(progress_percent)s,
                    %(total_items)s, %(completed_items)s, %(status)s, %(error_message)s, %(retry_count)s
                )
                ON CONFLICT (task_id) DO UPDATE SET
                    last_completed_date = EXCLUDED.last_completed_date,
                    completed_symbols = EXCLUDED.completed_symbols,
                    progress_percent = EXCLUDED.progress_percent,
                    total_items = EXCLUDED.total_items,
                    completed_items = EXCLUDED.completed_items,
                    status = EXCLUDED.status,
                    error_message = EXCLUDED.error_message,
                    retry_count = EXCLUDED.retry_count,
                    updated_at = CURRENT_TIMESTAMP
            """

            self.db.execute_query(sql, data)
            logger.debug(f"保存检查点: {checkpoint.task_id}, 进度: {checkpoint.progress_percent:.1f}%")
            return True

        except Exception as e:
            logger.error(f"保存检查点失败: {checkpoint.task_id}, 错误: {e}")
            return False

    def load_checkpoint(self, task_id: str) -> Optional[DownloadCheckpoint]:
        """
        加载下载检查点

        Args:
            task_id: 任务ID

        Returns:
            检查点数据，不存在返回None
        """
        try:
            sql = """
                SELECT * FROM download_checkpoints
                WHERE task_id = %s
            """
            rows = self.db.execute_query(sql, (task_id,))

            if not rows:
                return None

            row = rows[0]

            # 解析JSON字段
            symbols = json.loads(row['symbols']) if row['symbols'] else None
            completed_symbols = json.loads(row['completed_symbols']) if row['completed_symbols'] else None

            checkpoint = DownloadCheckpoint(
                task_id=row['task_id'],
                data_type=row['data_type'],
                symbol=row['symbol'],
                symbols=symbols,
                start_date=row['start_date'],
                end_date=row['end_date'],
                last_completed_date=row['last_completed_date'],
                completed_symbols=completed_symbols,
                progress_percent=float(row['progress_percent']),
                total_items=row['total_items'],
                completed_items=row['completed_items'],
                status=row['status'],
                error_message=row['error_message'],
                retry_count=row['retry_count'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )

            logger.debug(f"加载检查点: {task_id}, 状态: {checkpoint.status}, 进度: {checkpoint.progress_percent:.1f}%")
            return checkpoint

        except Exception as e:
            logger.error(f"加载检查点失败: {task_id}, 错误: {e}")
            return None

    def update_progress(
        self,
        task_id: str,
        completed_items: int,
        total_items: Optional[int] = None,
        last_completed_date: Optional[date] = None,
        completed_symbols: Optional[List[str]] = None
    ) -> bool:
        """
        更新下载进度

        Args:
            task_id: 任务ID
            completed_items: 已完成项目数
            total_items: 总项目数（可选）
            last_completed_date: 最后完成的日期（可选）
            completed_symbols: 已完成的股票代码列表（可选）

        Returns:
            是否更新成功
        """
        try:
            # 计算进度百分比
            checkpoint = self.load_checkpoint(task_id)
            if not checkpoint:
                logger.warning(f"检查点不存在: {task_id}")
                return False

            if total_items is not None:
                checkpoint.total_items = total_items

            checkpoint.completed_items = completed_items
            checkpoint.progress_percent = (completed_items / max(1, checkpoint.total_items)) * 100

            if last_completed_date:
                checkpoint.last_completed_date = last_completed_date

            if completed_symbols:
                checkpoint.completed_symbols = completed_symbols

            return self.save_checkpoint(checkpoint)

        except Exception as e:
            logger.error(f"更新进度失败: {task_id}, 错误: {e}")
            return False

    def mark_completed(self, task_id: str) -> bool:
        """
        标记任务为已完成

        Args:
            task_id: 任务ID

        Returns:
            是否标记成功
        """
        try:
            sql = """
                UPDATE download_checkpoints
                SET status = 'completed',
                    progress_percent = 100.0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = %s
            """
            self.db.execute_query(sql, (task_id,))
            logger.info(f"任务已完成: {task_id}")

            # 记录日志
            self.log_event(task_id, 'completed', '下载任务已完成')
            return True

        except Exception as e:
            logger.error(f"标记完成失败: {task_id}, 错误: {e}")
            return False

    def mark_failed(self, task_id: str, error_message: str) -> bool:
        """
        标记任务为失败

        Args:
            task_id: 任务ID
            error_message: 错误信息

        Returns:
            是否标记成功
        """
        try:
            sql = """
                UPDATE download_checkpoints
                SET status = 'failed',
                    error_message = %s,
                    retry_count = retry_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = %s
            """
            self.db.execute_query(sql, (error_message, task_id))
            logger.warning(f"任务失败: {task_id}, 错误: {error_message}")

            # 记录日志
            self.log_event(task_id, 'failed', error_message)
            return True

        except Exception as e:
            logger.error(f"标记失败失败: {task_id}, 错误: {e}")
            return False

    def clear_checkpoint(self, task_id: str) -> bool:
        """
        清除检查点

        Args:
            task_id: 任务ID

        Returns:
            是否清除成功
        """
        try:
            sql = "DELETE FROM download_checkpoints WHERE task_id = %s"
            self.db.execute_query(sql, (task_id,))
            logger.debug(f"清除检查点: {task_id}")
            return True

        except Exception as e:
            logger.error(f"清除检查点失败: {task_id}, 错误: {e}")
            return False

    def get_pending_tasks(self, data_type: Optional[str] = None) -> List[DownloadCheckpoint]:
        """
        获取待处理的任务（running或failed状态）

        Args:
            data_type: 数据类型过滤（可选）

        Returns:
            待处理任务列表
        """
        try:
            sql = """
                SELECT * FROM download_checkpoints
                WHERE status IN ('running', 'failed', 'paused')
            """
            params = []

            if data_type:
                sql += " AND data_type = %s"
                params.append(data_type)

            sql += " ORDER BY updated_at DESC"

            rows = self.db.execute_query(sql, tuple(params) if params else None)

            checkpoints = []
            for row in rows:
                symbols = json.loads(row['symbols']) if row['symbols'] else None
                completed_symbols = json.loads(row['completed_symbols']) if row['completed_symbols'] else None

                checkpoint = DownloadCheckpoint(
                    task_id=row['task_id'],
                    data_type=row['data_type'],
                    symbol=row['symbol'],
                    symbols=symbols,
                    start_date=row['start_date'],
                    end_date=row['end_date'],
                    last_completed_date=row['last_completed_date'],
                    completed_symbols=completed_symbols,
                    progress_percent=float(row['progress_percent']),
                    total_items=row['total_items'],
                    completed_items=row['completed_items'],
                    status=row['status'],
                    error_message=row['error_message'],
                    retry_count=row['retry_count'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at']
                )
                checkpoints.append(checkpoint)

            logger.info(f"找到 {len(checkpoints)} 个待处理任务")
            return checkpoints

        except Exception as e:
            logger.error(f"获取待处理任务失败: {e}")
            return []

    def cleanup_old_checkpoints(self, days: int = 7) -> int:
        """
        清理旧的已完成检查点

        Args:
            days: 保留天数

        Returns:
            清理的记录数
        """
        try:
            sql = """
                DELETE FROM download_checkpoints
                WHERE status = 'completed'
                AND updated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """
            result = self.db.execute_query(sql, (days,))
            count = result if isinstance(result, int) else 0
            logger.info(f"清理了 {count} 个旧检查点（>{days}天）")
            return count

        except Exception as e:
            logger.error(f"清理旧检查点失败: {e}")
            return 0

    def log_event(
        self,
        task_id: str,
        event_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        记录下载事件日志

        Args:
            task_id: 任务ID
            event_type: 事件类型
            message: 日志消息
            details: 详细信息

        Returns:
            是否记录成功
        """
        try:
            sql = """
                INSERT INTO download_task_logs (task_id, event_type, message, details)
                VALUES (%s, %s, %s, %s)
            """
            details_json = json.dumps(details) if details else None
            self.db.execute_query(sql, (task_id, event_type, message, details_json))
            return True

        except Exception as e:
            logger.error(f"记录日志失败: {task_id}, 错误: {e}")
            return False

    def get_task_logs(self, task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取任务日志

        Args:
            task_id: 任务ID
            limit: 最大记录数

        Returns:
            日志列表
        """
        try:
            sql = """
                SELECT * FROM download_task_logs
                WHERE task_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """
            rows = self.db.execute_query(sql, (task_id, limit))
            return [dict(row) for row in rows] if rows else []

        except Exception as e:
            logger.error(f"获取任务日志失败: {task_id}, 错误: {e}")
            return []
