"""
同步状态管理器
负责同步任务的状态管理和追踪
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager

from app.core.exceptions import ConfigError, DatabaseError
from app.repositories.config_repository import ConfigRepository
from app.repositories.sync_log_repository import SyncLogRepository


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
        self.config_repo = ConfigRepository(db)
        self.sync_log_repo = SyncLogRepository(db)

    # ==================== 全局同步状态 ====================

    async def get_sync_status(self) -> Dict:
        """
        获取全局同步状态

        Returns:
            Dict: 同步状态信息
        """
        try:
            keys = [
                "sync_status",
                "last_sync_date",
                "sync_progress",
                "sync_total",
                "sync_completed",
            ]

            configs = await asyncio.to_thread(self.config_repo.get_configs_by_keys, keys)

            return {
                "status": configs.get("sync_status") or "idle",
                "last_sync_date": configs.get("last_sync_date") or "",
                "progress": int(configs.get("sync_progress") or 0),
                "total": int(configs.get("sync_total") or 0),
                "completed": int(configs.get("sync_completed") or 0),
            }

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            raise ConfigError(
                "同步状态获取失败", error_code="SYNC_STATUS_FETCH_FAILED", reason=str(e)
            )

    async def update_sync_status(
        self,
        status: Optional[str] = None,
        last_sync_date: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None,
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
                updates["sync_status"] = status

            if last_sync_date is not None:
                updates["last_sync_date"] = last_sync_date

            if progress is not None:
                updates["sync_progress"] = str(progress)

            if total is not None:
                updates["sync_total"] = str(total)

            if completed is not None:
                updates["sync_completed"] = str(completed)

            if updates:
                await asyncio.to_thread(self.config_repo.set_configs_batch, updates)

            return await self.get_sync_status()

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"更新同步状态失败: {e}")
            raise ConfigError(
                "同步状态更新失败", error_code="SYNC_STATUS_UPDATE_FAILED", reason=str(e)
            )

    async def reset_sync_status(self) -> Dict:
        """
        重置全局同步状态

        Returns:
            Dict: 重置后的同步状态
        """
        return await self.update_sync_status(status="idle", progress=0, total=0, completed=0)

    # ==================== 中止标志管理 ====================

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """
        设置同步中止标志

        Args:
            abort: True表示请求中止，False表示清除中止标志
        """
        try:
            await asyncio.to_thread(
                self.config_repo.set_config_value, "sync_abort_flag", "true" if abort else "false"
            )
            logger.info(f"同步中止标志已设置为: {abort}")

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"设置同步中止标志失败: {e}")
            raise ConfigError(
                "同步中止标志设置失败",
                error_code="SYNC_ABORT_FLAG_SET_FAILED",
                abort=abort,
                reason=str(e),
            )

    async def check_sync_abort_flag(self) -> bool:
        """
        检查是否有中止同步的请求

        Returns:
            bool: True表示应该中止，False表示继续
        """
        try:
            flag = await asyncio.to_thread(self.config_repo.get_config_value, "sync_abort_flag")
            return flag == "true"

        except (DatabaseError, ConfigError) as e:
            # 配置读取失败，为安全起见返回False（不中止）
            logger.error(f"检查同步中止标志失败: {e}")
            return False
        except Exception as e:
            # 其他未预期错误，为安全起见返回False（不中止）
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
            # 使用 Repository 查询
            record = await asyncio.to_thread(self.sync_log_repo.get_latest_by_module, module)

            if record:
                return {
                    "status": record.get("status") or "idle",
                    "total": record.get("total_count") or 0,
                    "success": record.get("success_count") or 0,
                    "failed": record.get("failed_count") or 0,
                    "progress": record.get("progress") or 0,
                    "error_message": record.get("error_message") or "",
                    "started_at": record.get("started_at") or "",
                    "completed_at": record.get("completed_at") or "",
                }
            else:
                # 没有记录，返回空闲状态
                return {
                    "status": "idle",
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "progress": 0,
                    "error_message": "",
                    "started_at": "",
                    "completed_at": "",
                }

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取模块同步状态失败 ({module}): {e}")
            raise DatabaseError(
                f"模块同步状态查询失败: {module}",
                error_code="MODULE_SYNC_STATUS_QUERY_FAILED",
                module=module,
                reason=str(e),
            )

    # ==================== 同步任务管理 ====================

    async def create_sync_task(self, task_id: str, module: str, data_source: str) -> None:
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
        """
        try:
            # 使用 Repository 创建任务
            await asyncio.to_thread(
                self.sync_log_repo.create_task, task_id, module, data_source, "manual"
            )

            logger.info(f"✓ 创建同步任务: {task_id} ({module})")

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"创建同步任务失败: {e}")
            raise DatabaseError(
                "同步任务创建失败",
                error_code="SYNC_TASK_CREATE_FAILED",
                task_id=task_id,
                module=module,
                reason=str(e),
            )

    async def update_sync_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
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
            # 使用 Repository 更新任务
            await asyncio.to_thread(
                self.sync_log_repo.update_task,
                task_id=task_id,
                status=status,
                total_count=total_count,
                success_count=success_count,
                failed_count=failed_count,
                progress=progress,
                error_message=error_message,
            )

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"更新同步任务失败: {e}")
            raise DatabaseError(
                "同步任务更新失败",
                error_code="SYNC_TASK_UPDATE_FAILED",
                task_id=task_id,
                reason=str(e),
            )

    async def get_sync_task(self, task_id: str) -> Optional[Dict]:
        """
        获取同步任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息字典
        """
        try:
            # 使用 Repository 查询任务
            record = await asyncio.to_thread(self.sync_log_repo.get_by_task_id, task_id)
            return record

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取同步任务失败: {e}")
            raise DatabaseError(
                "同步任务查询失败",
                error_code="SYNC_TASK_QUERY_FAILED",
                task_id=task_id,
                reason=str(e),
            )
