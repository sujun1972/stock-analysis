"""
同步状态管理器
负责同步任务的状态管理和追踪
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from src.database.db_manager import DatabaseManager
from app.repositories.config_repository import ConfigRepository


class SyncStatusManager:
    """
    同步状态管理器

    职责：
    - 全局同步状态管理
    - 同步任务记录CRUD
    - 模块同步状态查询
    - 中止标志管理
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化同步状态管理器

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()
        self.config_repo = ConfigRepository(self.db)

    # ==================== 全局同步状态 ====================

    async def get_sync_status(self) -> Dict:
        """
        获取全局同步状态

        Returns:
            Dict: 同步状态信息
        """
        try:
            keys = [
                'sync_status',
                'last_sync_date',
                'sync_progress',
                'sync_total',
                'sync_completed'
            ]

            configs = await asyncio.to_thread(
                self.config_repo.get_configs_by_keys,
                keys
            )

            return {
                'status': configs.get('sync_status') or 'idle',
                'last_sync_date': configs.get('last_sync_date') or '',
                'progress': int(configs.get('sync_progress') or 0),
                'total': int(configs.get('sync_total') or 0),
                'completed': int(configs.get('sync_completed') or 0)
            }

        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            raise

    async def update_sync_status(
        self,
        status: Optional[str] = None,
        last_sync_date: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None
    ) -> Dict:
        """
        更新全局同步状态

        Args:
            status: 同步状态
            last_sync_date: 最后同步日期
            progress: 进度百分比
            total: 总数
            completed: 已完成数

        Returns:
            Dict: 更新后的同步状态
        """
        try:
            updates = {}

            if status is not None:
                updates['sync_status'] = status

            if last_sync_date is not None:
                updates['last_sync_date'] = last_sync_date

            if progress is not None:
                updates['sync_progress'] = str(progress)

            if total is not None:
                updates['sync_total'] = str(total)

            if completed is not None:
                updates['sync_completed'] = str(completed)

            if updates:
                await asyncio.to_thread(
                    self.config_repo.set_configs_batch,
                    updates
                )

            return await self.get_sync_status()

        except Exception as e:
            logger.error(f"更新同步状态失败: {e}")
            raise

    async def reset_sync_status(self) -> Dict:
        """
        重置全局同步状态

        Returns:
            Dict: 重置后的同步状态
        """
        return await self.update_sync_status(
            status='idle',
            progress=0,
            total=0,
            completed=0
        )

    # ==================== 中止标志管理 ====================

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """
        设置同步中止标志

        Args:
            abort: True表示请求中止，False表示清除中止标志
        """
        try:
            await asyncio.to_thread(
                self.config_repo.set_config_value,
                'sync_abort_flag',
                'true' if abort else 'false'
            )
            logger.info(f"同步中止标志已设置为: {abort}")

        except Exception as e:
            logger.error(f"设置同步中止标志失败: {e}")
            raise

    async def check_sync_abort_flag(self) -> bool:
        """
        检查是否有中止同步的请求

        Returns:
            bool: True表示应该中止，False表示继续
        """
        try:
            flag = await asyncio.to_thread(
                self.config_repo.get_config_value,
                'sync_abort_flag'
            )
            return flag == 'true'

        except Exception as e:
            logger.error(f"检查同步中止标志失败: {e}")
            return False

    async def clear_sync_abort_flag(self) -> None:
        """清除同步中止标志"""
        await self.set_sync_abort_flag(False)

    # ==================== 模块同步状态 ====================

    async def get_module_sync_status(self, module: str) -> Dict:
        """
        获取特定模块的同步状态（从 sync_log 表）

        Args:
            module: 模块名称 (stock_list, daily, minute, realtime)

        Returns:
            Dict: 模块同步状态信息
        """
        try:
            # 查询该模块最近的同步记录
            query = """
                SELECT
                    status,
                    total_count,
                    success_count,
                    failed_count,
                    progress,
                    error_message,
                    started_at,
                    completed_at
                FROM sync_log
                WHERE data_type = %s
                ORDER BY started_at DESC
                LIMIT 1
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query,
                (module,)
            )

            if result and len(result) > 0:
                row = result[0]
                return {
                    'status': row[0] or 'idle',
                    'total': row[1] or 0,
                    'success': row[2] or 0,
                    'failed': row[3] or 0,
                    'progress': row[4] or 0,
                    'error_message': row[5] or '',
                    'started_at': row[6].strftime('%Y-%m-%d %H:%M:%S') if row[6] else '',
                    'completed_at': row[7].strftime('%Y-%m-%d %H:%M:%S') if row[7] else ''
                }
            else:
                # 没有记录，返回空闲状态
                return {
                    'status': 'idle',
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'progress': 0,
                    'error_message': '',
                    'started_at': '',
                    'completed_at': ''
                }

        except Exception as e:
            logger.error(f"获取模块同步状态失败 ({module}): {e}")
            raise

    # ==================== 同步任务管理 ====================

    async def create_sync_task(
        self,
        task_id: str,
        module: str,
        data_source: str
    ) -> None:
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
        """
        try:
            query = """
                INSERT INTO sync_log (
                    task_id, task_type, data_type, data_source, status
                ) VALUES (%s, %s, %s, %s, %s)
            """

            await asyncio.to_thread(
                self.db._execute_update,
                query,
                (task_id, 'manual', module, data_source, 'running')
            )

            logger.info(f"✓ 创建同步任务: {task_id} ({module})")

        except Exception as e:
            logger.error(f"创建同步任务失败: {e}")
            raise

    async def update_sync_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        更新同步任务状态

        Args:
            task_id: 任务ID
            status: 状态
            total_count: 总数
            success_count: 成功数
            failed_count: 失败数
            progress: 进度
            error_message: 错误信息
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
            if status in ['completed', 'failed']:
                updates.append("completed_at = CURRENT_TIMESTAMP")
                updates.append("duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))::INTEGER")

            if not updates:
                return

            query = f"""
                UPDATE sync_log
                SET {', '.join(updates)}
                WHERE task_id = %s
            """
            params.append(task_id)

            await asyncio.to_thread(
                self.db._execute_update,
                query,
                tuple(params)
            )

        except Exception as e:
            logger.error(f"更新同步任务失败: {e}")
            raise

    async def get_sync_task(self, task_id: str) -> Optional[Dict]:
        """
        获取同步任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典
        """
        try:
            query = """
                SELECT
                    task_id, task_type, data_type, data_source, status,
                    total_count, success_count, failed_count, progress,
                    error_message, started_at, completed_at, duration_seconds
                FROM sync_log
                WHERE task_id = %s
            """

            result = await asyncio.to_thread(
                self.db._execute_query,
                query,
                (task_id,)
            )

            if not result:
                return None

            row = result[0]
            return {
                'task_id': row[0],
                'task_type': row[1],
                'data_type': row[2],
                'data_source': row[3],
                'status': row[4],
                'total_count': row[5],
                'success_count': row[6],
                'failed_count': row[7],
                'progress': row[8],
                'error_message': row[9],
                'started_at': row[10].isoformat() if row[10] else None,
                'completed_at': row[11].isoformat() if row[11] else None,
                'duration_seconds': row[12]
            }

        except Exception as e:
            logger.error(f"获取同步任务失败: {e}")
            raise
