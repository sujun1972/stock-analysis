"""
配置管理服务（Facade 模式，保持向后兼容）

委托给三个专门的服务类：
- SystemConfigService: 通用系统配置
- DataSourceConfigService: Tushare Token / 全量同步起始日期
- SyncStatusManager: 同步状态管理
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager

from app.core.exceptions import ConfigError, DatabaseError
from app.services.data_source_config_service import DataSourceConfigService
from app.services.sync_status_manager import SyncStatusManager
from app.services.system_config_service import SystemConfigService


class ConfigService:
    """配置管理服务（Facade 模式，向后兼容）。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化服务（Facade 模式）

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        # 委托给专门的服务
        self.system_config = SystemConfigService(db)
        self.data_source_config = DataSourceConfigService(db)
        self.sync_status_manager = SyncStatusManager(db)

        # 保留旧的引用名（向后兼容）
        self.data_source_manager = self.data_source_config

        logger.info("✓ ConfigService initialized (Facade mode)")

    # ==================== 通用配置接口（委托给 SystemConfigService）====================

    async def get_config(self, key: str) -> Optional[str]:
        """
        获取单个配置值

        Args:
            key: 配置键名

        Returns:
            Optional[str]: 配置值，不存在则返回 None
        """
        return await self.system_config.get_config(key)

    async def get_all_configs(self) -> Dict[str, str]:
        """
        获取所有配置

        Returns:
            Dict[str, str]: 配置字典
        """
        return await self.system_config.get_all_configs()

    async def set_config(self, key: str, value: str, description: str = "") -> bool:
        """
        设置单个配置值

        Args:
            key: 配置键名
            value: 配置值
            description: 配置描述（可选）

        Returns:
            bool: 是否成功
        """
        return await self.system_config.set_config(key, value, description)

    # ==================== 数据源配置接口（委托给 DataSourceConfigService）====================

    async def get_data_source_config(self, mask_token: bool = True) -> Dict:
        """
        获取数据源配置

        Args:
            mask_token: 是否对 Token 进行脱敏处理（默认 True）

        Returns:
            Dict: 包含 tushare_token 和 earliest_history_date
        """
        return await self.data_source_config.get_data_source_config(mask_token=mask_token)

    async def update_data_source(
        self,
        tushare_token: Optional[str] = None,
        earliest_history_date: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        更新数据源配置（Token 和全量同步最早日期）

        Args:
            tushare_token: Tushare Token (可选，留空不修改)
            earliest_history_date: 全量同步最早日期（可选）
            max_requests_per_minute: 每分钟最大请求数，0 表示不限速（可选）

        Returns:
            Dict: 更新后的配置
        """
        return await self.data_source_config.update_data_source(
            tushare_token=tushare_token,
            earliest_history_date=earliest_history_date,
            max_requests_per_minute=max_requests_per_minute,
        )

    # ==================== 同步状态接口（委托给 SyncStatusManager）====================

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
        return await self.sync_status_manager.update_sync_status(
            status=status,
            last_sync_date=last_sync_date,
            progress=progress,
            total=total,
            completed=completed,
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

    async def create_sync_task(self, task_id: str, module: str, data_source: str) -> None:
        """
        创建同步任务记录

        Args:
            task_id: 任务ID
            module: 模块名称
            data_source: 数据源
        """
        await self.sync_status_manager.create_sync_task(
            task_id=task_id, module=module, data_source=data_source
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
        await self.sync_status_manager.update_sync_task(
            task_id=task_id,
            status=status,
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            progress=progress,
            error_message=error_message,
        )
