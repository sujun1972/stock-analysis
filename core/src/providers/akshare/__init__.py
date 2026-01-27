"""
AkShare 数据提供者模块

提供基于 AkShare 的股票数据获取功能。

模块结构:
- provider.py: 主提供者类
- api_client.py: API 客户端封装
- data_converter.py: 数据格式转换
- config.py: 配置常量
- exceptions.py: 自定义异常

使用示例:
    >>> from src.providers.akshare import AkShareProvider
    >>> provider = AkShareProvider()
    >>> df = provider.get_stock_list()
"""

from .provider import AkShareProvider
from .exceptions import (
    AkShareError,
    AkShareImportError,
    AkShareDataError,
    AkShareRateLimitError,
    AkShareTimeoutError,
    AkShareNetworkError
)

__all__ = [
    'AkShareProvider',
    'AkShareError',
    'AkShareImportError',
    'AkShareDataError',
    'AkShareRateLimitError',
    'AkShareTimeoutError',
    'AkShareNetworkError',
]

__version__ = '2.0.0'
