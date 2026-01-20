"""
数据提供者模块
提供统一的数据接口抽象层
"""

from .base_provider import BaseDataProvider
from .akshare_provider import AkShareProvider
from .tushare_provider import TushareProvider
from .provider_factory import DataProviderFactory

__all__ = [
    'BaseDataProvider',
    'AkShareProvider',
    'TushareProvider',
    'DataProviderFactory'
]
