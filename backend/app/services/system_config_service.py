"""
系统配置服务
管理通用系统配置

职责：
1. 通用配置的读写操作
2. 配置的批量管理
3. 配置的缓存和验证

重构说明：
- 从 ConfigService 提取通用配置管理逻辑
- 专注于系统级配置（非数据源、非同步状态）
- 提供统一的配置访问接口
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager

from app.core.exceptions import ConfigError, DatabaseError
from app.repositories.config_repository import ConfigRepository


class SystemConfigService:
    """
    系统配置服务

    职责：
    - 管理系统级配置项
    - 配置的CRUD操作
    - 配置验证和缓存
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化系统配置服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.config_repo = ConfigRepository(db)
        logger.debug("✓ SystemConfigService initialized")

    # ==================== 基础配置操作 ====================

    async def get_config(self, key: str) -> Optional[str]:
        """
        获取单个配置值

        Args:
            key: 配置键

        Returns:
            配置值，如果不存在则返回 None

        Examples:
            >>> value = await service.get_config('app_name')
            >>> print(f"应用名称: {value}")
        """
        try:
            value = await asyncio.to_thread(self.config_repo.get_config_value, key)
            return value
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取配置失败 (key={key}): {e}")
            raise ConfigError(
                f"配置 '{key}' 获取失败",
                error_code="CONFIG_GET_FAILED",
                config_key=key,
                reason=str(e)
            )

    async def set_config(self, key: str, value: str, description: str = "") -> bool:
        """
        设置单个配置值

        Args:
            key: 配置键
            value: 配置值
            description: 配置描述（可选，仅在新建时使用）

        Returns:
            是否成功

        Examples:
            >>> await service.set_config('app_name', 'Stock Analysis', 'Application name')
        """
        try:
            await asyncio.to_thread(self.config_repo.set_config_value, key, value, description)
            logger.info(f"✓ 配置已更新: {key}")
            return True
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"设置配置失败 (key={key}): {e}")
            raise ConfigError(
                f"配置 '{key}' 设置失败",
                error_code="CONFIG_SET_FAILED",
                config_key=key,
                reason=str(e)
            )

    async def get_all_configs(self) -> Dict[str, str]:
        """
        获取所有配置

        Returns:
            配置字典 {key: value}

        Examples:
            >>> configs = await service.get_all_configs()
            >>> for key, value in configs.items():
            ...     print(f"{key}: {value}")
        """
        try:
            configs = await asyncio.to_thread(self.config_repo.get_all_configs)
            return configs
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
            raise ConfigError(
                "获取所有配置失败",
                error_code="CONFIG_GET_ALL_FAILED",
                reason=str(e)
            )

    # ==================== 批量操作 ====================

    async def get_configs_by_keys(self, keys: list[str]) -> Dict[str, Optional[str]]:
        """
        批量获取配置

        Args:
            keys: 配置键列表

        Returns:
            配置字典 {key: value}，不存在的键值为 None

        Examples:
            >>> configs = await service.get_configs_by_keys(['app_name', 'version'])
            >>> print(configs)
            {'app_name': 'Stock Analysis', 'version': '1.0.0'}
        """
        try:
            configs = await asyncio.to_thread(self.config_repo.get_configs_by_keys, keys)
            return configs
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"批量获取配置失败: {e}")
            raise ConfigError(
                "批量获取配置失败",
                error_code="CONFIG_BATCH_GET_FAILED",
                keys=keys,
                reason=str(e)
            )

    async def set_configs_batch(self, configs: Dict[str, str]) -> bool:
        """
        批量设置配置

        Args:
            configs: 配置字典 {key: value}

        Returns:
            是否成功

        Examples:
            >>> await service.set_configs_batch({
            ...     'app_name': 'Stock Analysis',
            ...     'version': '1.0.0'
            ... })
        """
        try:
            await asyncio.to_thread(self.config_repo.set_configs_batch, configs)
            logger.info(f"✓ 批量配置已更新: {len(configs)} 项")
            return True
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"批量设置配置失败: {e}")
            raise ConfigError(
                "批量设置配置失败",
                error_code="CONFIG_BATCH_SET_FAILED",
                count=len(configs),
                reason=str(e)
            )

    # ==================== 配置检查 ====================

    async def config_exists(self, key: str) -> bool:
        """
        检查配置是否存在

        Args:
            key: 配置键

        Returns:
            是否存在
        """
        try:
            value = await self.get_config(key)
            return value is not None
        except Exception:
            return False

    async def delete_config(self, key: str) -> bool:
        """
        删除配置

        Args:
            key: 配置键

        Returns:
            是否成功

        Examples:
            >>> await service.delete_config('old_config_key')
        """
        try:
            await asyncio.to_thread(self.config_repo.delete_config, key)
            logger.info(f"✓ 配置已删除: {key}")
            return True
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"删除配置失败 (key={key}): {e}")
            raise ConfigError(
                f"配置 '{key}' 删除失败",
                error_code="CONFIG_DELETE_FAILED",
                config_key=key,
                reason=str(e)
            )

    # ==================== 便捷方法 ====================

    async def get_config_with_default(self, key: str, default: str) -> str:
        """
        获取配置值（带默认值）

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值或默认值

        Examples:
            >>> timeout = await service.get_config_with_default('timeout', '30')
        """
        value = await self.get_config(key)
        return value if value is not None else default

    async def get_config_as_int(self, key: str, default: int = 0) -> int:
        """
        获取配置值并转换为整数

        Args:
            key: 配置键
            default: 默认值

        Returns:
            整数值

        Examples:
            >>> max_retries = await service.get_config_as_int('max_retries', 3)
        """
        value = await self.get_config(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            logger.warning(f"配置 '{key}' 不是有效的整数，使用默认值 {default}")
            return default

    async def get_config_as_bool(self, key: str, default: bool = False) -> bool:
        """
        获取配置值并转换为布尔值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            布尔值

        Examples:
            >>> debug_mode = await service.get_config_as_bool('debug_mode', False)
        """
        value = await self.get_config(key)
        if value is None:
            return default

        # 支持多种布尔值表示
        true_values = {'true', '1', 'yes', 'on', 'enabled'}
        false_values = {'false', '0', 'no', 'off', 'disabled'}

        value_lower = value.lower().strip()
        if value_lower in true_values:
            return True
        elif value_lower in false_values:
            return False
        else:
            logger.warning(f"配置 '{key}' 不是有效的布尔值，使用默认值 {default}")
            return default
