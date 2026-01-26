"""
数据提供者模块
提供统一的数据接口抽象层

重构说明（2026-01-26）：
- 模块化重构：拆分元数据管理和注册中心
- 新增 provider_metadata.py：元数据定义
- 新增 provider_registry.py：注册中心实现
- 优化 provider_factory.py：外观模式入口
- 统一使用项目 logger
"""

from .base_provider import BaseDataProvider
from .akshare_provider import AkShareProvider
from .tushare_provider import TushareProvider
from .provider_metadata import ProviderMetadata
from .provider_registry import ProviderRegistry
from .provider_factory import (
    DataProviderFactory,
    provider,
    get_provider,
    register_provider,
    list_providers,
)

__all__ = [
    # 基础类
    'BaseDataProvider',
    # 内置提供者
    'AkShareProvider',
    'TushareProvider',
    # 元数据和注册
    'ProviderMetadata',
    'ProviderRegistry',
    # 工厂类
    'DataProviderFactory',
    # 装饰器
    'provider',
    # 便捷函数
    'get_provider',
    'register_provider',
    'list_providers',
]
