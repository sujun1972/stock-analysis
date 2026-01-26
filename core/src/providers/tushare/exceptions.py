"""
Tushare 提供者自定义异常

定义特定的异常类型，便于错误处理和日志记录
"""


class TushareException(Exception):
    """Tushare 相关异常的基类"""
    pass


class TushareConfigError(TushareException):
    """Tushare 配置错误"""
    pass


class TushareTokenError(TushareConfigError):
    """Tushare Token 错误"""
    pass


class TusharePermissionError(TushareException):
    """Tushare 权限不足或积分不足"""
    pass


class TushareRateLimitError(TushareException):
    """Tushare 频率限制错误"""

    def __init__(self, message: str, retry_after: int = 60):
        """
        初始化频率限制错误

        Args:
            message: 错误消息
            retry_after: 建议重试等待时间（秒）
        """
        super().__init__(message)
        self.retry_after = retry_after


class TushareDataError(TushareException):
    """Tushare 数据错误（空数据、格式错误等）"""
    pass


class TushareAPIError(TushareException):
    """Tushare API 调用错误"""
    pass
