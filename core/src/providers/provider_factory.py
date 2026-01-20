"""
数据提供者工厂
根据配置动态创建数据提供者实例
"""

from typing import Optional, Dict
from loguru import logger

from .base_provider import BaseDataProvider
from .akshare_provider import AkShareProvider
from .tushare_provider import TushareProvider


class DataProviderFactory:
    """
    数据提供者工厂类

    负责根据配置创建合适的数据提供者实例
    支持运行时动态切换数据源
    """

    # 注册的提供者类
    _providers: Dict[str, type] = {
        'akshare': AkShareProvider,
        'tushare': TushareProvider
    }

    @classmethod
    def create_provider(
        cls,
        source: str,
        **kwargs
    ) -> BaseDataProvider:
        """
        创建数据提供者实例

        Args:
            source: 数据源名称 ('akshare' 或 'tushare')
            **kwargs: 提供者特定的配置参数
                - token: Tushare Token (Tushare 必需)
                - timeout: 请求超时时间
                - retry_count: 重试次数
                - retry_delay: 重试延迟
                - request_delay: 请求间隔

        Returns:
            BaseDataProvider: 数据提供者实例

        Raises:
            ValueError: 不支持的数据源
            Exception: 创建失败

        Examples:
            >>> # 创建 AkShare 提供者
            >>> provider = DataProviderFactory.create_provider('akshare')
            >>>
            >>> # 创建 Tushare 提供者
            >>> provider = DataProviderFactory.create_provider(
            ...     'tushare',
            ...     token='your_token_here'
            ... )
        """
        source = source.lower().strip()

        if source not in cls._providers:
            raise ValueError(
                f"不支持的数据源: {source}. "
                f"支持的数据源: {', '.join(cls._providers.keys())}"
            )

        try:
            provider_class = cls._providers[source]
            provider = provider_class(**kwargs)

            logger.info(f"✓ 成功创建数据提供者: {provider}")

            return provider

        except Exception as e:
            logger.error(f"创建数据提供者失败 ({source}): {e}")
            raise

    @classmethod
    def register_provider(
        cls,
        name: str,
        provider_class: type
    ) -> None:
        """
        注册新的数据提供者

        Args:
            name: 提供者名称
            provider_class: 提供者类（必须继承 BaseDataProvider）

        Raises:
            TypeError: 提供者类不是 BaseDataProvider 的子类
        """
        if not issubclass(provider_class, BaseDataProvider):
            raise TypeError(
                f"{provider_class} 必须继承 BaseDataProvider"
            )

        cls._providers[name.lower()] = provider_class
        logger.info(f"注册数据提供者: {name}")

    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的数据提供者名称

        Returns:
            list: 数据提供者名称列表
        """
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, source: str) -> bool:
        """
        检查数据提供者是否可用

        Args:
            source: 数据源名称

        Returns:
            bool: 是否可用
        """
        return source.lower() in cls._providers
