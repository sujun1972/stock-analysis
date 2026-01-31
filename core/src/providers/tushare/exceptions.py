"""
Tushare 提供者自定义异常

定义特定的异常类型，便于错误处理和日志记录。

该模块已迁移到统一异常系统，所有异常类继承自src.exceptions中的基类，
同时保持向后兼容性。

Migration Notes:
    - TushareException 现在继承自 DataProviderError
    - TushareConfigError 继承自 ConfigError
    - 使用统一的错误代码和上下文信息机制
    - TushareRateLimitError.retry_after 现在通过context传递
    - 完全向后兼容：现有代码无需修改

Examples:
    >>> # 新用法：使用错误代码和上下文
    >>> raise TushareDataError(
    ...     "获取股票数据失败",
    ...     error_code="TUSHARE_API_ERROR",
    ...     stock_code="000001.SZ",
    ...     api_name="daily",
    ...     fields="ts_code,trade_date,close"
    ... )

    >>> # 频率限制错误
    >>> raise TushareRateLimitError(
    ...     "API调用频率超限",
    ...     error_code="TUSHARE_RATE_LIMIT",
    ...     retry_after=60,
    ...     api_name="daily",
    ...     points_used=2000
    ... )
"""

from src.exceptions import DataProviderError, ConfigError


class TushareException(DataProviderError):
    """Tushare 相关异常的基类

    继承自统一异常系统的DataProviderError，支持错误代码和上下文信息。

    Attributes:
        message: 错误消息
        error_code: 错误代码（默认为类名）
        context: 上下文信息字典

    Examples:
        >>> raise TushareException(
        ...     "Tushare操作失败",
        ...     error_code="TUSHARE_ERROR",
        ...     provider="tushare",
        ...     operation="query_data"
        ... )
    """
    pass


class TushareConfigError(ConfigError):
    """Tushare 配置错误

    继承自ConfigError，用于配置相关的异常。

    Examples:
        >>> raise TushareConfigError(
        ...     "Tushare配置缺失",
        ...     error_code="TUSHARE_CONFIG_MISSING",
        ...     missing_key="tushare_token",
        ...     config_file="config.yaml"
        ... )
    """
    pass


class TushareTokenError(TushareConfigError):
    """Tushare Token 错误

    当Token缺失、无效或过期时抛出。

    Examples:
        >>> raise TushareTokenError(
        ...     "Tushare Token无效",
        ...     error_code="INVALID_TOKEN",
        ...     token_length=len(token),
        ...     suggestion="请检查config.yaml中的tushare_token配置"
        ... )
    """
    pass


class TusharePermissionError(TushareException):
    """Tushare 权限不足或积分不足

    当用户权限不足或积分不足以调用某个API时抛出。

    Examples:
        >>> raise TusharePermissionError(
        ...     "权限不足，无法访问该接口",
        ...     error_code="INSUFFICIENT_PERMISSION",
        ...     api_name="index_weight",
        ...     required_points=5000,
        ...     user_points=2000
        ... )
    """
    pass


class TushareRateLimitError(TushareException):
    """Tushare 频率限制错误

    当API调用频率超过限制时抛出。retry_after通过context传递。

    Attributes:
        message: 错误消息
        error_code: 错误代码
        context: 包含retry_after等信息的上下文字典

    Migration Note:
        旧代码: exception.retry_after
        新代码: exception.context.get('retry_after', 60)
        兼容: 提供retry_after属性以保持向后兼容

    Examples:
        >>> raise TushareRateLimitError(
        ...     "API调用频率超限",
        ...     error_code="RATE_LIMIT_EXCEEDED",
        ...     retry_after=60,
        ...     api_name="daily",
        ...     limit_per_minute=200
        ... )
    """

    def __init__(self, message: str, error_code: str = None, retry_after: int = 60, **context):
        """
        初始化频率限制错误

        Args:
            message: 错误消息
            error_code: 错误代码
            retry_after: 建议重试等待时间（秒），默认60秒
            **context: 其他上下文信息
        """
        # 将retry_after添加到context中
        context['retry_after'] = retry_after
        super().__init__(message, error_code=error_code, **context)

    @property
    def retry_after(self) -> int:
        """向后兼容属性：获取retry_after值"""
        return self.context.get('retry_after', 60)


class TushareDataError(TushareException):
    """Tushare 数据错误（空数据、格式错误等）

    当返回的数据为空、格式不正确或包含异常值时抛出。

    Examples:
        >>> raise TushareDataError(
        ...     "返回数据为空",
        ...     error_code="EMPTY_DATA",
        ...     stock_code="000001.SZ",
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     api_name="daily"
        ... )
    """
    pass


class TushareAPIError(TushareException):
    """Tushare API 调用错误

    当API调用本身失败时抛出（网络错误、超时、服务器错误等）。

    Examples:
        >>> raise TushareAPIError(
        ...     "API调用失败",
        ...     error_code="API_CALL_FAILED",
        ...     api_name="daily",
        ...     http_status=500,
        ...     response_message="Internal Server Error"
        ... )
    """
    pass


__all__ = [
    'TushareException',
    'TushareConfigError',
    'TushareTokenError',
    'TusharePermissionError',
    'TushareRateLimitError',
    'TushareDataError',
    'TushareAPIError',
]
