"""
数据提供者注册中心模块

负责数据提供者的注册、查询和管理，实现：
- 提供者注册/注销
- 提供者查询和过滤
- 内置提供者初始化
- 线程安全的注册表管理
"""

from typing import Dict, Type, List, Optional
import inspect
import threading

from src.utils.logger import get_logger
from .provider_metadata import ProviderMetadata

# 获取模块专用 logger
logger = get_logger(__name__)


class ProviderRegistry:
    """
    数据提供者注册中心

    单例模式实现，提供线程安全的提供者注册表管理。
    职责：
    - 维护全局提供者注册表
    - 提供者注册/注销
    - 提供者查询和过滤
    - 元数据管理
    """

    # 类级别的注册表（所有实例共享）
    _providers: Dict[str, ProviderMetadata] = {}
    _lock = threading.RLock()  # 可重入锁，支持递归调用
    _initialized = False

    @classmethod
    def initialize_builtin_providers(cls) -> None:
        """
        初始化内置提供者

        只在第一次调用时执行，后续调用会被忽略。
        使用双重检查锁定模式确保线程安全。
        """
        if cls._initialized:
            return

        with cls._lock:
            # 双重检查：防止多线程重复初始化
            if cls._initialized:
                return

            # 延迟导入，避免循环依赖
            from .akshare import AkShareProvider  # 从新的模块化结构导入
            from .tushare import TushareProvider  # 从新的模块化结构导入

            # 注册 AkShare
            cls._register_provider(
                name='akshare',
                provider_class=AkShareProvider,
                description="AkShare 数据源（免费，无需 Token）",
                requires_token=False,
                features=['stock_list', 'daily_data', 'realtime_quotes', 'minute_data'],
                priority=10
            )

            # 注册 Tushare
            cls._register_provider(
                name='tushare',
                provider_class=TushareProvider,
                description="Tushare Pro 数据源（需要 Token 和积分）",
                requires_token=True,
                features=['stock_list', 'daily_data', 'realtime_quotes', 'minute_data', 'financial_data'],
                priority=20
            )

            cls._initialized = True
            logger.debug("内置数据提供者初始化完成")

    @classmethod
    def _register_provider(
        cls,
        name: str,
        provider_class: Type,
        description: str = "",
        requires_token: bool = False,
        features: Optional[List[str]] = None,
        priority: int = 0,
        override: bool = False
    ) -> None:
        """
        内部注册方法（不加锁，由调用者控制）

        Args:
            name: 提供者名称
            provider_class: 提供者类
            description: 描述信息
            requires_token: 是否需要 Token
            features: 支持的特性列表
            priority: 优先级
            override: 是否允许覆盖
        """
        # 验证类型
        if not inspect.isclass(provider_class):
            raise TypeError(f"{provider_class} 不是一个类")

        # 导入基类进行验证（延迟导入避免循环依赖）
        from .base_provider import BaseDataProvider
        if not issubclass(provider_class, BaseDataProvider):
            raise TypeError(f"{provider_class.__name__} 必须继承 BaseDataProvider")

        # 规范化名称
        name = name.lower().strip()

        # 检查是否已存在
        if name in cls._providers and not override:
            raise ValueError(
                f"提供者 '{name}' 已存在。如需覆盖，请设置 override=True"
            )

        # 创建元数据
        metadata = ProviderMetadata(
            provider_class=provider_class,
            description=description,
            requires_token=requires_token,
            features=features or [],
            priority=priority
        )

        # 注册
        is_override = name in cls._providers
        cls._providers[name] = metadata

        logger.info(
            f"{'覆盖' if is_override else '注册'}数据提供者: {name} "
            f"({provider_class.__name__}, priority={priority})"
        )

    @classmethod
    def register(
        cls,
        name: str,
        provider_class: Type,
        description: str = "",
        requires_token: bool = False,
        features: Optional[List[str]] = None,
        priority: int = 0,
        override: bool = False
    ) -> None:
        """
        注册数据提供者（公共接口，带锁）

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
            >>> ProviderRegistry.register(
            ...     'yahoo',
            ...     YahooFinanceProvider,
            ...     description="Yahoo Finance 数据源",
            ...     requires_token=False,
            ...     features=['stock_list', 'daily_data'],
            ...     priority=15
            ... )
        """
        with cls._lock:
            cls._register_provider(
                name=name,
                provider_class=provider_class,
                description=description,
                requires_token=requires_token,
                features=features,
                priority=priority,
                override=override
            )

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销数据提供者

        Args:
            name: 提供者名称

        Returns:
            bool: 是否成功注销
        """
        with cls._lock:
            name = name.lower().strip()

            if name in cls._providers:
                del cls._providers[name]
                logger.info(f"注销数据提供者: {name}")
                return True

            return False

    @classmethod
    def get(cls, name: str) -> Optional[ProviderMetadata]:
        """
        获取提供者元数据

        Args:
            name: 提供者名称

        Returns:
            ProviderMetadata: 元数据对象，不存在返回 None
        """
        cls.initialize_builtin_providers()

        with cls._lock:
            name = name.lower().strip()
            return cls._providers.get(name)

    @classmethod
    def exists(cls, name: str) -> bool:
        """
        检查提供者是否存在

        Args:
            name: 提供者名称

        Returns:
            bool: 是否存在
        """
        cls.initialize_builtin_providers()

        with cls._lock:
            return name.lower() in cls._providers

    @classmethod
    def get_all(cls) -> Dict[str, ProviderMetadata]:
        """
        获取所有注册的提供者

        Returns:
            Dict[str, ProviderMetadata]: 提供者字典（副本）
        """
        cls.initialize_builtin_providers()

        with cls._lock:
            return cls._providers.copy()

    @classmethod
    def get_names(cls, sort_by_priority: bool = True) -> List[str]:
        """
        获取所有提供者名称

        Args:
            sort_by_priority: 是否按优先级排序（默认 True）

        Returns:
            List[str]: 提供者名称列表
        """
        cls.initialize_builtin_providers()

        with cls._lock:
            if sort_by_priority:
                # 按优先级降序排序
                sorted_items = sorted(
                    cls._providers.items(),
                    key=lambda x: x[1].priority,
                    reverse=True
                )
                return [name for name, _ in sorted_items]
            else:
                return list(cls._providers.keys())

    @classmethod
    def filter_by_feature(cls, feature: str) -> List[str]:
        """
        根据特性筛选提供者

        Args:
            feature: 特性名称（如 'realtime_quotes', 'financial_data'）

        Returns:
            List[str]: 支持该特性的提供者名称列表（按优先级排序）
        """
        cls.initialize_builtin_providers()

        with cls._lock:
            providers = [
                (name, metadata)
                for name, metadata in cls._providers.items()
                if metadata.has_feature(feature)
            ]

            # 按优先级降序排序
            providers.sort(key=lambda x: x[1].priority, reverse=True)

            return [name for name, _ in providers]

    @classmethod
    def get_default(cls) -> str:
        """
        获取默认提供者（优先级最高的）

        Returns:
            str: 默认提供者名称

        Raises:
            ValueError: 没有可用的提供者
        """
        names = cls.get_names(sort_by_priority=True)

        if not names:
            raise ValueError("没有可用的数据提供者")

        return names[0]

    @classmethod
    def clear(cls) -> None:
        """
        清空注册表（主要用于测试）

        Warning:
            此操作会清空所有已注册的提供者，包括内置提供者。
            需要重新调用 initialize_builtin_providers() 初始化。
        """
        with cls._lock:
            cls._providers.clear()
            cls._initialized = False
            logger.warning("提供者注册表已清空")


__all__ = ['ProviderRegistry']
