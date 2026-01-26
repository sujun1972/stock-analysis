"""
数据提供者工厂模式实现

通过工厂模式和注册机制，实现可插拔的数据提供者架构。
支持动态注册、运行时切换和插件化扩展。

重构说明：
- 提取元数据管理到 provider_metadata.py
- 提取注册中心到 provider_registry.py
- 工厂类作为外观模式的入口
- 统一使用项目 logger
"""

from typing import Optional, Dict, Type, Any, List

from src.utils.logger import get_logger
from .base_provider import BaseDataProvider
from .provider_metadata import ProviderMetadata
from .provider_registry import ProviderRegistry

# 获取模块专用 logger
logger = get_logger(__name__)


class DataProviderFactory:
    """
    数据提供者工厂类（外观模式）

    提供简化的接口，委托给 ProviderRegistry 处理实际逻辑。

    实现完善的工厂模式，支持：
    - 动态注册：运行时注册新的提供者
    - 元数据管理：提供者特性和优先级
    - 自动发现：通过装饰器自动注册
    - 验证机制：类型检查和配置验证
    - 插件化扩展：支持第三方提供者
    """

    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type[BaseDataProvider],
        description: str = "",
        requires_token: bool = False,
        features: Optional[List[str]] = None,
        priority: int = 0,
        override: bool = False
    ) -> None:
        """
        注册数据提供者

        Args:
            name: 提供者名称（小写）
            provider_class: 提供者类（必须继承 BaseDataProvider）
            description: 描述信息
            requires_token: 是否需要 Token
            features: 支持的特性列表
            priority: 优先级（数字越大优先级越高）
            override: 是否允许覆盖已有提供者

        Raises:
            TypeError: 提供者类不是 BaseDataProvider 的子类
            ValueError: 提供者已存在且不允许覆盖

        Examples:
            >>> # 注册自定义提供者
            >>> DataProviderFactory.register(
            ...     'yahoo',
            ...     YahooFinanceProvider,
            ...     description="Yahoo Finance 数据源",
            ...     requires_token=False,
            ...     features=['stock_list', 'daily_data'],
            ...     priority=15
            ... )
        """
        ProviderRegistry.register(
            name=name,
            provider_class=provider_class,
            description=description,
            requires_token=requires_token,
            features=features,
            priority=priority,
            override=override
        )

    @classmethod
    def create_provider(
        cls,
        source: str,
        **kwargs
    ) -> BaseDataProvider:
        """
        创建数据提供者实例

        Args:
            source: 数据源名称 ('akshare', 'tushare', 或其他已注册的提供者)
            **kwargs: 提供者特定的配置参数
                - token: API Token (部分提供者必需)
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
            >>>
            >>> # 创建自定义提供者
            >>> provider = DataProviderFactory.create_provider(
            ...     'yahoo',
            ...     api_key='your_key'
            ... )
        """
        # 规范化名称
        source = source.lower().strip()

        # 从注册中心获取元数据
        metadata = ProviderRegistry.get(source)

        if metadata is None:
            available = ', '.join(ProviderRegistry.get_names())
            raise ValueError(
                f"不支持的数据源: '{source}'\n"
                f"可用的数据源: {available}\n"
                f"提示: 使用 DataProviderFactory.register() 注册新提供者"
            )

        # 验证必需参数
        if metadata.requires_token and 'token' not in kwargs:
            logger.warning(
                f"提供者 '{source}' 需要 Token，但未提供。"
                f"某些功能可能无法使用。"
            )

        try:
            # 创建实例
            provider_class = metadata.provider_class
            provider = provider_class(**kwargs)

            logger.info(
                f"✓ 成功创建数据提供者: {source} "
                f"({provider_class.__name__})"
            )

            return provider

        except Exception as e:
            logger.error(
                f"创建数据提供者失败 ({source}): {e}\n"
                f"请检查配置参数是否正确"
            )
            raise

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        获取所有可用的数据提供者名称

        Returns:
            List[str]: 数据提供者名称列表（按优先级排序）
        """
        return ProviderRegistry.get_names(sort_by_priority=True)

    @classmethod
    def is_provider_available(cls, source: str) -> bool:
        """
        检查数据提供者是否可用

        Args:
            source: 数据源名称

        Returns:
            bool: 是否可用
        """
        return ProviderRegistry.exists(source)

    @classmethod
    def get_provider_info(cls, source: str) -> Dict[str, Any]:
        """
        获取数据提供者的详细信息

        Args:
            source: 数据源名称

        Returns:
            Dict[str, Any]: 提供者信息字典

        Raises:
            ValueError: 提供者不存在
        """
        source = source.lower().strip()

        metadata = ProviderRegistry.get(source)

        if metadata is None:
            raise ValueError(f"提供者 '{source}' 不存在")

        return {
            'name': source,
            **metadata.to_dict()
        }

    @classmethod
    def list_all_providers(cls) -> List[Dict[str, Any]]:
        """
        列出所有已注册的提供者及其信息

        Returns:
            List[Dict[str, Any]]: 提供者信息列表
        """
        providers_info = []

        for name in cls.get_available_providers():
            providers_info.append(cls.get_provider_info(name))

        return providers_info

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销数据提供者

        Args:
            name: 提供者名称

        Returns:
            bool: 是否成功注销
        """
        return ProviderRegistry.unregister(name)

    @classmethod
    def get_provider_by_feature(cls, feature: str) -> List[str]:
        """
        根据特性查找支持的提供者

        Args:
            feature: 特性名称（如 'realtime_quotes', 'financial_data'）

        Returns:
            List[str]: 支持该特性的提供者名称列表（按优先级排序）
        """
        return ProviderRegistry.filter_by_feature(feature)

    @classmethod
    def get_default_provider(cls) -> str:
        """
        获取默认的数据提供者（优先级最高的）

        Returns:
            str: 默认提供者名称

        Raises:
            ValueError: 没有可用的数据提供者
        """
        return ProviderRegistry.get_default()

    @classmethod
    def create_default_provider(cls, **kwargs) -> BaseDataProvider:
        """
        创建默认的数据提供者实例

        Args:
            **kwargs: 提供者配置参数

        Returns:
            BaseDataProvider: 提供者实例
        """
        default_name = cls.get_default_provider()
        logger.info(f"使用默认数据提供者: {default_name}")
        return cls.create_provider(default_name, **kwargs)


# ==================== 装饰器支持 ====================

def provider(
    name: str,
    description: str = "",
    requires_token: bool = False,
    features: Optional[List[str]] = None,
    priority: int = 0
):
    """
    装饰器：自动注册数据提供者

    使用装饰器可以在定义类时自动注册到工厂

    Args:
        name: 提供者名称
        description: 描述信息
        requires_token: 是否需要 Token
        features: 支持的特性列表
        priority: 优先级

    Examples:
        >>> @provider(
        ...     name='yahoo',
        ...     description="Yahoo Finance 数据源",
        ...     features=['stock_list', 'daily_data'],
        ...     priority=15
        ... )
        >>> class YahooFinanceProvider(BaseDataProvider):
        ...     pass
    """
    def decorator(cls):
        # 注册提供者
        DataProviderFactory.register(
            name=name,
            provider_class=cls,
            description=description,
            requires_token=requires_token,
            features=features,
            priority=priority,
            override=True  # 装饰器允许覆盖
        )
        return cls

    return decorator


# ==================== 便捷函数 ====================

def get_provider(source: str, **kwargs) -> BaseDataProvider:
    """
    便捷函数：获取数据提供者实例

    Args:
        source: 数据源名称
        **kwargs: 配置参数

    Returns:
        BaseDataProvider: 提供者实例
    """
    return DataProviderFactory.create_provider(source, **kwargs)


def register_provider(
    name: str,
    provider_class: Type[BaseDataProvider],
    **metadata
) -> None:
    """
    便捷函数：注册数据提供者

    Args:
        name: 提供者名称
        provider_class: 提供者类
        **metadata: 元数据（description, requires_token, features, priority）
    """
    DataProviderFactory.register(name, provider_class, **metadata)


def list_providers() -> List[str]:
    """
    便捷函数：列出所有可用的提供者

    Returns:
        List[str]: 提供者名称列表
    """
    return DataProviderFactory.get_available_providers()


# ==================== 导出 ====================

__all__ = [
    # 主要类
    'DataProviderFactory',
    'ProviderMetadata',
    # 装饰器
    'provider',
    # 便捷函数
    'get_provider',
    'register_provider',
    'list_providers',
]
