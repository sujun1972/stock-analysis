"""
数据提供者工厂模式实现

通过工厂模式和注册机制，实现可插拔的数据提供者架构。
支持动态注册、运行时切换和插件化扩展。
"""

from typing import Optional, Dict, Type, Any, List, Callable
from loguru import logger
import inspect
from functools import wraps

from .base_provider import BaseDataProvider
from .akshare_provider import AkShareProvider
from .tushare_provider import TushareProvider


class ProviderMetadata:
    """数据提供者元数据"""

    def __init__(
        self,
        provider_class: Type[BaseDataProvider],
        description: str = "",
        requires_token: bool = False,
        features: List[str] = None,
        priority: int = 0
    ):
        """
        初始化元数据

        Args:
            provider_class: 提供者类
            description: 描述信息
            requires_token: 是否需要 Token
            features: 支持的特性列表
            priority: 优先级（数字越大优先级越高）
        """
        self.provider_class = provider_class
        self.description = description
        self.requires_token = requires_token
        self.features = features or []
        self.priority = priority

    def __repr__(self) -> str:
        return (
            f"ProviderMetadata(class={self.provider_class.__name__}, "
            f"requires_token={self.requires_token}, priority={self.priority})"
        )


class DataProviderFactory:
    """
    数据提供者工厂类

    实现完善的工厂模式，支持：
    - 动态注册：运行时注册新的提供者
    - 元数据管理：提供者特性和优先级
    - 自动发现：通过装饰器自动注册
    - 验证机制：类型检查和配置验证
    - 插件化扩展：支持第三方提供者
    """

    # 注册的提供者（名称 -> 元数据）
    _providers: Dict[str, ProviderMetadata] = {}

    # 初始化时注册内置提供者
    @classmethod
    def _init_builtin_providers(cls) -> None:
        """初始化内置提供者"""
        if not cls._providers:
            cls.register(
                'akshare',
                AkShareProvider,
                description="AkShare 数据源（免费，无需 Token）",
                requires_token=False,
                features=['stock_list', 'daily_data', 'realtime_quotes', 'minute_data'],
                priority=10
            )
            cls.register(
                'tushare',
                TushareProvider,
                description="Tushare Pro 数据源（需要 Token 和积分）",
                requires_token=True,
                features=['stock_list', 'daily_data', 'realtime_quotes', 'minute_data', 'financial_data'],
                priority=20
            )

    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type[BaseDataProvider],
        description: str = "",
        requires_token: bool = False,
        features: List[str] = None,
        priority: int = 0,
        override: bool = False
    ) -> None:
        """
        注册数据提供者（增强版）

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
        # 验证类型
        if not inspect.isclass(provider_class):
            raise TypeError(f"{provider_class} 不是一个类")

        if not issubclass(provider_class, BaseDataProvider):
            raise TypeError(
                f"{provider_class.__name__} 必须继承 BaseDataProvider"
            )

        # 规范化名称
        name = name.lower().strip()

        # 检查是否已存在
        if name in cls._providers and not override:
            raise ValueError(
                f"提供者 '{name}' 已存在。如需覆盖，请设置 override=True"
            )

        # 创建元数据并注册
        metadata = ProviderMetadata(
            provider_class=provider_class,
            description=description,
            requires_token=requires_token,
            features=features or [],
            priority=priority
        )

        cls._providers[name] = metadata

        logger.info(
            f"{'覆盖' if name in cls._providers else '注册'}数据提供者: {name} "
            f"({provider_class.__name__}, priority={priority})"
        )

    @classmethod
    def create_provider(
        cls,
        source: str,
        **kwargs
    ) -> BaseDataProvider:
        """
        创建数据提供者实例（增强版）

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
        # 初始化内置提供者
        cls._init_builtin_providers()

        # 规范化名称
        source = source.lower().strip()

        # 检查提供者是否存在
        if source not in cls._providers:
            available = ', '.join(cls.get_available_providers())
            raise ValueError(
                f"不支持的数据源: '{source}'\n"
                f"可用的数据源: {available}\n"
                f"提示: 使用 DataProviderFactory.register() 注册新提供者"
            )

        # 获取元数据
        metadata = cls._providers[source]

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
        cls._init_builtin_providers()

        # 按优先级排序
        sorted_providers = sorted(
            cls._providers.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )

        return [name for name, _ in sorted_providers]

    @classmethod
    def is_provider_available(cls, source: str) -> bool:
        """
        检查数据提供者是否可用

        Args:
            source: 数据源名称

        Returns:
            bool: 是否可用
        """
        cls._init_builtin_providers()
        return source.lower() in cls._providers

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
        cls._init_builtin_providers()

        source = source.lower().strip()

        if source not in cls._providers:
            raise ValueError(f"提供者 '{source}' 不存在")

        metadata = cls._providers[source]

        return {
            'name': source,
            'class': metadata.provider_class.__name__,
            'description': metadata.description,
            'requires_token': metadata.requires_token,
            'features': metadata.features,
            'priority': metadata.priority,
        }

    @classmethod
    def list_all_providers(cls) -> List[Dict[str, Any]]:
        """
        列出所有已注册的提供者及其信息

        Returns:
            List[Dict[str, Any]]: 提供者信息列表
        """
        cls._init_builtin_providers()

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
        name = name.lower().strip()

        if name in cls._providers:
            del cls._providers[name]
            logger.info(f"注销数据提供者: {name}")
            return True

        return False

    @classmethod
    def get_provider_by_feature(cls, feature: str) -> List[str]:
        """
        根据特性查找支持的提供者

        Args:
            feature: 特性名称（如 'realtime_quotes', 'financial_data'）

        Returns:
            List[str]: 支持该特性的提供者名称列表
        """
        cls._init_builtin_providers()

        providers = []

        for name, metadata in cls._providers.items():
            if feature in metadata.features:
                providers.append(name)

        # 按优先级排序
        providers.sort(
            key=lambda x: cls._providers[x].priority,
            reverse=True
        )

        return providers

    @classmethod
    def get_default_provider(cls) -> str:
        """
        获取默认的数据提供者（优先级最高的）

        Returns:
            str: 默认提供者名称
        """
        providers = cls.get_available_providers()

        if not providers:
            raise ValueError("没有可用的数据提供者")

        return providers[0]  # 已按优先级排序

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
    features: List[str] = None,
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
    'DataProviderFactory',
    'ProviderMetadata',
    'provider',
    'get_provider',
    'register_provider',
    'list_providers',
]
