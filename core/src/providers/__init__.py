"""
数据提供者模块
提供统一的数据接口抽象层

重构说明（2026-01-26）：
- 模块化重构：拆分元数据管理和注册中心
- 新增 provider_metadata.py：元数据定义
- 新增 provider_registry.py：注册中心实现
- 优化 provider_factory.py：外观模式入口
- 统一使用项目 logger

重构说明（2026-01-27）：
- Tushare Provider 模块化重构：拆分为独立的 tushare 子包
- AkShare Provider 模块化重构：拆分为独立的 akshare 子包
- 保持向后兼容的导入路径
"""

from .base_provider import BaseDataProvider
# 从新的模块化结构中导入（保持向后兼容）
from .akshare import AkShareProvider
from .tushare import TushareProvider
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
