"""
Tushare 数据提供者模块

模块化重构后的 Tushare Provider 实现
将原有的单文件拆分为多个子模块，提高可维护性和可测试性

模块结构:
- config.py: 配置常量和元数据
- exceptions.py: 自定义异常类
- api_client.py: API 客户端封装（重试、限流、错误处理）
- data_converter.py: 数据转换器（标准化输出）
- provider.py: 主 Provider 类（实现 BaseDataProvider 接口）

使用示例:
    from src.providers.tushare import TushareProvider

    provider = TushareProvider(token='your_token')
    stock_list = provider.get_stock_list()
"""

from .provider import TushareProvider
from .config import TushareConfig, TushareErrorMessages, TushareFields
from .exceptions import (
    TushareException,
    TushareConfigError,
    TushareTokenError,
    TusharePermissionError,
    TushareRateLimitError,
    TushareDataError,
    TushareAPIError
)
from .api_client import TushareAPIClient
from .data_converter import TushareDataConverter

__all__ = [
    # 主类
    'TushareProvider',

    # 配置
    'TushareConfig',
    'TushareErrorMessages',
    'TushareFields',

    # 异常
    'TushareException',
    'TushareConfigError',
    'TushareTokenError',
    'TusharePermissionError',
    'TushareRateLimitError',
    'TushareDataError',
    'TushareAPIError',

    # 组件（供高级用户使用）
    'TushareAPIClient',
    'TushareDataConverter',
]
