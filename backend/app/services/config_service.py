"""
配置管理服务（重构版）
使用 Facade 模式委托给专门的服务类
"""

from typing import Optional, Dict
from loguru import logger
import asyncio
from src.database.db_manager import DatabaseManager

from app.repositories.config_repository import ConfigRepository
from app.services.data_source_manager import DataSourceManager
from app.services.sync_status_manager import SyncStatusManager


class ConfigService:
    """
    配置管理服务（Facade模式）

    将配置管理、数据源管理和同步状态管理功能委托给专门的服务类，
    提供统一的接口供API层调用。
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """初始化服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        # 委托给专门的服务
        self.config_repo = ConfigRepository(db)
        self.data_source_manager = DataSourceManager(db)
        self.sync_status_manager = SyncStatusManager(db)

        logger.info("✓ ConfigService initialized")

    # ==================== 通用配置接口 ====================

    async def get_config(self, key: str) -> Optional[str]:
        """
        获取单个配置值

        Args:
            key: 配置键名

        Returns:
            Optional[str]: 配置值，不存在则返回 None
        """
        try:
            return await asyncio.to_thread(
                self.config_repo.get_config_value,
                key
            )
        except Exception as e:
            logger.error(f"获取配置失败 ({key}): {e}")
            raise

    async def get_all_configs(self) -> Dict[str, str]:
        """
        获取所有配置

        Returns:
            Dict[str, str]: 配置字典
        """
        try:
            return await asyncio.to_thread(
                self.config_repo.get_all_configs
            )
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            raise

    async def set_config(self, key: str, value: str) -> bool:
        """
        设置单个配置值

        Args:
            key: 配置键名
            value: 配置值

        Returns:
            bool: 是否成功
        """
        try:
            rows = await asyncio.to_thread(
                self.config_repo.set_config_value,
                key,
                value
            )
            return rows > 0
        except Exception as e:
            logger.error(f"设置配置失败 ({key}): {e}")
            raise

    # ==================== 数据源配置接口 ====================

    async def get_data_source_config(self) -> Dict:
        """
        获取数据源配置

        Returns:
            Dict: 包含 data_source、minute_data_source、realtime_data_source 和 tushare_token
        """
        return await self.data_source_manager.get_data_source_config()

    async def update_data_source(
        self,
        data_source: str,
        minute_data_source: Optional[str] = None,
        realtime_data_source: Optional[str] = None,
        tushare_token: Optional[str] = None
    ) -> Dict:
        """
        更新数据源配置

        Args:
            data_source: 主数据源 ('akshare' 或 'tushare')
            minute_data_source: 分时数据源
            realtime_data_source: 实时数据源
            tushare_token: Tushare Token (可选)

        Returns:
            Dict: 更新后的配置
        """
        return await self.data_source_manager.update_data_source(
            data_source=data_source,
            minute_data_source=minute_data_source,
            realtime_data_source=realtime_data_source,
            tushare_token=tushare_token
        )

    # ==================== 同步状态接口 ====================

    async def get_sync_status(self) -> Dict:
        """
        获取全局同步状态

        Returns:
            Dict: 同步状态信息
        """
        return await self.sync_status_manager.get_sync_status()

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
        return await self.sync_status_manager.update_sync_status(
            status=status,
            last_sync_date=last_sync_date,
            progress=progress,
            total=total,
            completed=completed
        )

    async def reset_sync_status(self) -> Dict:
        """
        重置全局同步状态

        Returns:
            Dict: 重置后的同步状态
        """
        return await self.sync_status_manager.reset_sync_status()

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """
        设置同步中止标志

        Args:
            abort: True表示请求中止，False表示清除中止标志
        """
        await self.sync_status_manager.set_sync_abort_flag(abort)

    async def check_sync_abort_flag(self) -> bool:
        """
        检查是否有中止同步的请求

        Returns:
            bool: True表示应该中止，False表示继续
        """
        return await self.sync_status_manager.check_sync_abort_flag()

    async def clear_sync_abort_flag(self) -> None:
        """清除同步中止标志"""
        await self.sync_status_manager.clear_sync_abort_flag()

    # ==================== 模块同步状态接口 ====================

    async def get_module_sync_status(self, module: str) -> Dict:
        """
        获取特定模块的同步状态

        Args:
            module: 模块名称 (stock_list, daily, minute, realtime)

        Returns:
            Dict: 模块同步状态信息
        """
        return await self.sync_status_manager.get_module_sync_status(module)

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
        await self.sync_status_manager.create_sync_task(
            task_id=task_id,
            module=module,
            data_source=data_source
        )

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
        await self.sync_status_manager.update_sync_task(
            task_id=task_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            progress=progress,
            error_message=error_message
        )
