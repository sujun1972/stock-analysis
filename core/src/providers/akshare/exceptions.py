"""
AkShare 提供者自定义异常

定义 AkShare 数据获取过程中可能出现的异常类型。

该模块已迁移到统一异常系统，所有异常类继承自src.exceptions中的基类，
同时保持向后兼容性。

Migration Notes:
    - AkShareError 现在继承自 DataProviderError
    - 所有子异常类使用统一的错误代码和上下文信息机制
    - 完全向后兼容：现有代码无需修改

Examples:
    >>> # 新用法：使用错误代码和上下文
    >>> raise AkShareDataError(
    ...     "获取股票数据失败",
    ...     error_code="AKSHARE_API_ERROR",
    ...     stock_code="000001",
    ...     api_function="stock_zh_a_hist"
    ... )

    >>> # 旧用法：仍然支持
    >>> raise AkShareDataError("获取股票数据失败")
"""

from src.exceptions import DataProviderError


class AkShareError(DataProviderError):
    """AkShare 基础异常类

    继承自统一异常系统的DataProviderError，支持错误代码和上下文信息。

    Attributes:
        message: 错误消息
        error_code: 错误代码（默认为类名）
        context: 上下文信息字典

    Examples:
        >>> raise AkShareError(
        ...     "AkShare操作失败",
        ...     error_code="AKSHARE_ERROR",
        ...     provider="akshare",
        ...     operation="get_stock_list"
        ... )
    """
    pass


class AkShareImportError(AkShareError):
    """AkShare 库未安装异常

    当系统检测到akshare库未安装时抛出。

    Examples:
        >>> raise AkShareImportError(
        ...     "akshare库未安装",
        ...     error_code="AKSHARE_NOT_INSTALLED",
        ...     suggestion="请运行: pip install akshare"
        ... )
    """
    pass


class AkShareDataError(AkShareError):
    """AkShare 数据获取失败异常

    当从AkShare API获取数据失败、数据为空或格式错误时抛出。

    Examples:
        >>> raise AkShareDataError(
        ...     "获取股票历史数据失败",
        ...     error_code="AKSHARE_DATA_ERROR",
        ...     stock_code="000001",
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-31",
        ...     api_function="stock_zh_a_hist"
        ... )
    """
    pass


class AkShareRateLimitError(AkShareError):
    """AkShare IP 限流异常

    当触发AkShare的IP限流机制时抛出。

    Examples:
        >>> raise AkShareRateLimitError(
        ...     "请求频率过高，IP被限流",
        ...     error_code="AKSHARE_RATE_LIMIT",
        ...     retry_after=60,
        ...     suggestion="请等待60秒后重试"
        ... )
    """
    pass


class AkShareTimeoutError(AkShareError):
    """AkShare 请求超时异常

    当AkShare API请求超时时抛出。

    Examples:
        >>> raise AkShareTimeoutError(
        ...     "API请求超时",
        ...     error_code="AKSHARE_TIMEOUT",
        ...     timeout_seconds=30,
        ...     api_endpoint="stock_zh_a_hist"
        ... )
    """
    pass


class AkShareNetworkError(AkShareError):
    """AkShare 网络连接异常

    当网络连接失败或不稳定时抛出。

    Examples:
        >>> raise AkShareNetworkError(
        ...     "网络连接失败",
        ...     error_code="AKSHARE_NETWORK_ERROR",
        ...     host="akshare.akfamily.xyz",
        ...     reason="连接被拒绝"
        ... )
    """
    pass


__all__ = [
    'AkShareError',
    'AkShareImportError',
    'AkShareDataError',
    'AkShareRateLimitError',
    'AkShareTimeoutError',
    'AkShareNetworkError',
]
