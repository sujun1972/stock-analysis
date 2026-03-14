"""
数据提供者服务
负责管理数据提供者的创建、缓存和连接验证

职责：
1. 根据模块动态创建对应的数据提供者实例
2. 缓存数据提供者实例，避免重复创建
3. 验证数据提供者连接状态
4. 处理数据提供者切换逻辑

重构说明：
- 从 DataDownloadService 提取数据提供者管理逻辑
- 依赖 DataSourceManager 获取配置，但专注于提供者实例管理
- 支持多模块独立数据源配置（主数据、分时、实时等7种）
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager
from src.providers import DataProviderFactory
from src.providers.base_provider import BaseDataProvider

from app.core.exceptions import ConfigError, ExternalAPIError
from app.services.data_source_config_service import DataSourceConfigService


class DataProviderService:
    """
    数据提供者服务

    职责：
    - 创建和缓存数据提供者实例
    - 管理不同模块的数据提供者
    - 验证提供者连接状态
    - 处理提供者生命周期

    支持的模块：
    - main: 主数据源（股票列表、日线数据）
    - minute: 分时数据源
    - realtime: 实时行情数据源
    - limit_up: 涨停板池数据源
    - top_list: 龙虎榜数据源
    - premarket: 盘前外盘数据源
    - concept: 概念板块数据源
    """

    # 模块到配置键的映射
    MODULE_CONFIG_MAP = {
        "main": "data_source",
        "minute": "minute_data_source",
        "realtime": "realtime_data_source",
        "limit_up": "limit_up_data_source",
        "top_list": "top_list_data_source",
        "premarket": "premarket_data_source",
        "concept": "concept_data_source",
    }

    def __init__(self, data_source_config: Optional[DataSourceConfigService] = None, db: Optional[DatabaseManager] = None):
        """
        初始化数据提供者服务

        Args:
            data_source_config: 数据源配置服务实例（可选，用于依赖注入）
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.data_source_config = data_source_config or DataSourceConfigService(db)
        self._provider_cache: Dict[str, BaseDataProvider] = {}
        self._config_cache: Optional[Dict] = None
        logger.info("✓ DataProviderService initialized")

    # ==================== 提供者创建和获取 ====================

    async def _get_config(self, force_refresh: bool = False) -> Dict:
        """
        获取数据源配置（带缓存）

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            数据源配置字典
        """
        if self._config_cache is None or force_refresh:
            self._config_cache = await self.data_source_config.get_data_source_config(mask_token=False)
        return self._config_cache

    def _get_provider_type_for_module(self, module: str, config: Dict) -> str:
        """
        获取指定模块的数据提供者类型

        Args:
            module: 模块名称
            config: 数据源配置

        Returns:
            提供者类型 ('akshare' 或 'tushare')

        Raises:
            ValueError: 不支持的模块名称
        """
        if module not in self.MODULE_CONFIG_MAP:
            raise ValueError(
                f"不支持的模块: {module}\n"
                f"支持的模块: {', '.join(self.MODULE_CONFIG_MAP.keys())}"
            )

        config_key = self.MODULE_CONFIG_MAP[module]
        provider_type = config.get(config_key, "akshare")

        logger.debug(f"模块 '{module}' 使用数据源: {provider_type}")
        return provider_type

    async def get_provider(
        self,
        module: str = "main",
        force_refresh: bool = False,
        retry_count: int = 3,
        **kwargs
    ) -> BaseDataProvider:
        """
        获取指定模块的数据提供者实例

        Args:
            module: 模块名称（main, minute, realtime等）
            force_refresh: 是否强制刷新（忽略缓存）
            retry_count: 重试次数
            **kwargs: 传递给提供者的额外参数

        Returns:
            数据提供者实例

        Raises:
            ConfigError: 配置错误
            ExternalAPIError: 提供者创建失败

        Examples:
            >>> # 获取主数据源提供者
            >>> provider = await service.get_provider('main')
            >>>
            >>> # 获取分时数据提供者
            >>> provider = await service.get_provider('minute')
            >>>
            >>> # 强制刷新缓存
            >>> provider = await service.get_provider('main', force_refresh=True)
        """
        try:
            # 如果需要刷新，清除缓存
            if force_refresh:
                self.invalidate_cache(module)

            # 检查缓存
            if module in self._provider_cache and not force_refresh:
                logger.debug(f"从缓存返回提供者: {module}")
                return self._provider_cache[module]

            # 获取配置
            config = await self._get_config(force_refresh=force_refresh)

            # 确定提供者类型
            provider_type = self._get_provider_type_for_module(module, config)

            # 创建提供者实例
            provider = await self.create_provider(
                provider_type=provider_type,
                token=config.get("tushare_token", ""),
                retry_count=retry_count,
                **kwargs
            )

            # 缓存实例
            self._provider_cache[module] = provider

            logger.info(f"✓ 为模块 '{module}' 创建数据提供者: {provider_type}")

            return provider

        except ValueError as e:
            # 模块名称无效
            raise ConfigError(
                str(e),
                error_code="INVALID_MODULE_NAME",
                module=module
            )
        except Exception as e:
            logger.error(f"获取数据提供者失败 (module={module}): {e}")
            raise ExternalAPIError(
                f"数据提供者获取失败 ({module})",
                error_code="PROVIDER_CREATION_FAILED",
                module=module,
                reason=str(e)
            )

    async def create_provider(
        self,
        provider_type: str,
        token: str = "",
        retry_count: int = 3,
        **kwargs
    ) -> BaseDataProvider:
        """
        创建数据提供者实例（不使用缓存）

        Args:
            provider_type: 提供者类型 ('akshare' 或 'tushare')
            token: API Token（Tushare需要）
            retry_count: 重试次数
            **kwargs: 额外的提供者参数

        Returns:
            数据提供者实例

        Raises:
            ValueError: 不支持的提供者类型
            ExternalAPIError: 创建失败
        """
        try:
            provider = await asyncio.to_thread(
                DataProviderFactory.create_provider,
                source=provider_type,
                token=token,
                retry_count=retry_count,
                **kwargs
            )

            logger.info(f"✓ 创建数据提供者: {provider_type}")
            return provider

        except ValueError as e:
            # 不支持的数据源
            available = ', '.join(DataProviderFactory.get_available_providers())
            raise ValueError(
                f"不支持的数据提供者: {provider_type}\n"
                f"可用的提供者: {available}"
            )
        except Exception as e:
            logger.error(f"创建数据提供者失败 ({provider_type}): {e}")
            raise ExternalAPIError(
                f"数据提供者创建失败 ({provider_type})",
                error_code="PROVIDER_INSTANTIATION_FAILED",
                provider_type=provider_type,
                reason=str(e)
            )

    # ==================== 连接测试和验证 ====================

    async def test_connection(self, module: str = "main") -> bool:
        """
        测试数据提供者连接

        Args:
            module: 模块名称

        Returns:
            是否连接成功

        Examples:
            >>> # 测试主数据源连接
            >>> is_ok = await service.test_connection('main')
            >>> if is_ok:
            ...     print("连接成功")
        """
        try:
            provider = await self.get_provider(module)

            # 尝试获取股票列表（轻量级测试）
            logger.info(f"测试提供者连接: {module}")
            response = await asyncio.to_thread(provider.get_stock_list)

            if response.is_success():
                logger.info(f"✓ 提供者连接正常: {module}")
                return True
            else:
                logger.warning(f"提供者连接失败: {module} - {response.error_message}")
                return False

        except Exception as e:
            logger.error(f"测试连接失败 ({module}): {e}")
            return False

    async def validate_provider(self, provider_type: str, token: Optional[str] = None) -> bool:
        """
        验证数据提供者配置是否有效

        Args:
            provider_type: 提供者类型
            token: API Token（可选）

        Returns:
            是否有效

        Examples:
            >>> # 验证 Tushare 配置
            >>> is_valid = await service.validate_provider('tushare', 'your_token')
        """
        try:
            # 检查提供者是否可用
            if not DataProviderFactory.is_provider_available(provider_type):
                logger.warning(f"提供者不可用: {provider_type}")
                return False

            # 检查是否需要 Token
            provider_info = DataProviderFactory.get_provider_info(provider_type)
            if provider_info.get('requires_token', False) and not token:
                logger.warning(f"提供者 {provider_type} 需要 Token")
                return False

            # 尝试创建实例
            provider = await self.create_provider(provider_type, token=token or "")

            logger.info(f"✓ 提供者配置有效: {provider_type}")
            return True

        except Exception as e:
            logger.error(f"提供者验证失败 ({provider_type}): {e}")
            return False

    # ==================== 缓存管理 ====================

    def invalidate_cache(self, module: Optional[str] = None) -> None:
        """
        清除缓存

        Args:
            module: 模块名称（None 表示清除所有缓存）

        Examples:
            >>> # 清除特定模块缓存
            >>> service.invalidate_cache('main')
            >>>
            >>> # 清除所有缓存
            >>> service.invalidate_cache()
        """
        if module is None:
            # 清除所有缓存
            self._provider_cache.clear()
            self._config_cache = None
            logger.info("✓ 已清除所有提供者缓存")
        else:
            # 清除特定模块缓存
            if module in self._provider_cache:
                del self._provider_cache[module]
                logger.info(f"✓ 已清除模块缓存: {module}")

    def get_cached_modules(self) -> list[str]:
        """
        获取已缓存的模块列表

        Returns:
            模块名称列表
        """
        return list(self._provider_cache.keys())

    # ==================== 便捷方法 ====================

    async def get_main_provider(self, **kwargs) -> BaseDataProvider:
        """获取主数据源提供者"""
        return await self.get_provider("main", **kwargs)

    async def get_minute_provider(self, **kwargs) -> BaseDataProvider:
        """获取分时数据提供者"""
        return await self.get_provider("minute", **kwargs)

    async def get_realtime_provider(self, **kwargs) -> BaseDataProvider:
        """获取实时数据提供者"""
        return await self.get_provider("realtime", **kwargs)

    async def get_concept_provider(self, **kwargs) -> BaseDataProvider:
        """获取概念数据提供者"""
        return await self.get_provider("concept", **kwargs)

    async def get_limit_up_provider(self, **kwargs) -> BaseDataProvider:
        """获取涨停板数据提供者"""
        return await self.get_provider("limit_up", **kwargs)

    async def get_top_list_provider(self, **kwargs) -> BaseDataProvider:
        """获取龙虎榜数据提供者"""
        return await self.get_provider("top_list", **kwargs)

    async def get_premarket_provider(self, **kwargs) -> BaseDataProvider:
        """获取盘前数据提供者"""
        return await self.get_provider("premarket", **kwargs)

    # ==================== 信息查询 ====================

    @staticmethod
    def get_available_providers() -> list[str]:
        """
        获取所有可用的数据提供者

        Returns:
            提供者名称列表
        """
        return DataProviderFactory.get_available_providers()

    @staticmethod
    def get_provider_info_static(provider_type: str) -> Dict:
        """
        获取提供者详细信息（静态方法）

        Args:
            provider_type: 提供者类型

        Returns:
            提供者信息字典
        """
        return DataProviderFactory.get_provider_info(provider_type)

    @staticmethod
    def get_supported_modules() -> list[str]:
        """
        获取支持的模块列表

        Returns:
            模块名称列表
        """
        return list(DataProviderService.MODULE_CONFIG_MAP.keys())
