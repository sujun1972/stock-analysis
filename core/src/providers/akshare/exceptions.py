"""
AkShare 提供者自定义异常

定义 AkShare 数据获取过程中可能出现的异常类型
"""


class AkShareError(Exception):
    """AkShare 基础异常类"""
    pass


class AkShareImportError(AkShareError):
    """AkShare 库未安装异常"""
    pass


class AkShareDataError(AkShareError):
    """AkShare 数据获取失败异常"""
    pass


class AkShareRateLimitError(AkShareError):
    """AkShare IP 限流异常"""
    pass


class AkShareTimeoutError(AkShareError):
    """AkShare 请求超时异常"""
    pass


class AkShareNetworkError(AkShareError):
    """AkShare 网络连接异常"""
    pass


__all__ = [
    'AkShareError',
    'AkShareImportError',
    'AkShareDataError',
    'AkShareRateLimitError',
    'AkShareTimeoutError',
    'AkShareNetworkError',
]
