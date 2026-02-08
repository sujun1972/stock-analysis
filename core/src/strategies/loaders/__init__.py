"""
策略加载器模块

提供多种策略加载方式:
- ConfigLoader: 从数据库加载参数配置（方案1）
- DynamicCodeLoader: 动态加载AI生成的代码（方案2）
- LoaderFactory: 统一的加载器工厂
"""

from .base_loader import BaseLoader
from .config_loader import ConfigLoader
from .dynamic_loader import DynamicCodeLoader
from .loader_factory import LoaderFactory

__all__ = [
    'BaseLoader',
    'ConfigLoader',
    'DynamicCodeLoader',
    'LoaderFactory',
]
