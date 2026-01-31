"""
错误处理工具模块

提供统一的错误处理装饰器和工具函数，简化异常处理逻辑。

该模块包含:
- handle_errors: 通用错误处理装饰器
- retry_on_error: 重试装饰器
- log_errors: 错误日志装饰器
- safe_execute: 安全执行函数

Examples:
    >>> from src.utils.error_handling import handle_errors
    >>> from src.exceptions import DataProviderError
    >>>
    >>> @handle_errors(DataProviderError, default_return=pd.DataFrame())
    >>> def fetch_stock_data(stock_code: str) -> pd.DataFrame:
    ...     return provider.get_daily_data(stock_code)
    ...
    >>> # 失败时返回空DataFrame，不会抛出异常
    >>> df = fetch_stock_data("INVALID")
"""
import time
import functools
from typing import Callable, Type, Any, Optional, TypeVar, Union, Tuple
from loguru import logger

from src.exceptions import StockAnalysisError


F = TypeVar('F', bound=Callable[..., Any])


def handle_errors(
    exception_class: Union[Type[Exception], Tuple[Type[Exception], ...]] = StockAnalysisError,
    default_return: Any = None,
    log_level: str = "error",
    reraise: bool = False,
    custom_message: Optional[str] = None
) -> Callable[[F], F]:
    """错误处理装饰器

    捕获指定的异常，记录日志，并可选择性地返回默认值或重新抛出。

    Args:
        exception_class: 要捕获的异常类或异常类元组
        default_return: 发生异常时的默认返回值，如果为None且reraise=False则返回None
        log_level: 日志级别，可选: "debug", "info", "warning", "error", "critical"
        reraise: 是否在记录日志后重新抛出异常
        custom_message: 自定义错误消息前缀

    Returns:
        装饰器函数

    Examples:
        >>> # 基本使用：捕获异常并返回默认值
        >>> @handle_errors(DataProviderError, default_return=pd.DataFrame())
        >>> def fetch_data(code: str) -> pd.DataFrame:
        ...     return provider.get_daily_data(code)
        ...
        >>> # 结果：失败时返回空DataFrame

        >>> # 捕获多种异常
        >>> @handle_errors((DataError, FeatureError), default_return=None)
        >>> def process_data(data):
        ...     return calculate_features(data)

        >>> # 记录日志但仍然抛出异常
        >>> @handle_errors(ModelError, reraise=True, log_level="critical")
        >>> def train_model(data):
        ...     return model.fit(data)

        >>> # 自定义错误消息
        >>> @handle_errors(
        ...     ConfigError,
        ...     custom_message="配置加载失败",
        ...     default_return={}
        ... )
        >>> def load_config():
        ...     return config_loader.load()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_class as e:
                # 获取日志函数
                log_func = getattr(logger, log_level, logger.error)

                # 构建日志消息
                func_name = func.__name__
                if custom_message:
                    message = f"{custom_message}: {func_name} 执行失败"
                else:
                    message = f"{func_name} 执行失败"

                # 记录日志
                if isinstance(e, StockAnalysisError):
                    # 对于自定义异常，记录详细的上下文信息
                    log_func(
                        f"{message}: {e.message}",
                        error_code=e.error_code,
                        error_type=e.__class__.__name__,
                        **e.context
                    )
                else:
                    # 对于标准异常，记录基本信息
                    log_func(f"{message}: {str(e)}", exception=str(e))

                # 重新抛出或返回默认值
                if reraise:
                    raise
                return default_return

        return wrapper  # type: ignore
    return decorator


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exception_class: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    reraise: bool = True,
    log_retries: bool = True
) -> Callable[[F], F]:
    """重试装饰器

    在函数执行失败时自动重试，支持指数退避策略。

    Args:
        max_attempts: 最大尝试次数（包括首次）
        delay: 首次重试延迟（秒）
        backoff_factor: 退避因子，每次重试延迟 = delay * (backoff_factor ^ retry_count)
        exception_class: 触发重试的异常类
        reraise: 所有重试失败后是否抛出异常
        log_retries: 是否记录重试日志

    Returns:
        装饰器函数

    Examples:
        >>> # 基本重试：最多3次，延迟1秒
        >>> @retry_on_error(max_attempts=3, delay=1.0)
        >>> def fetch_data_from_api():
        ...     return requests.get("https://api.example.com/data")

        >>> # 指数退避：1s, 2s, 4s
        >>> @retry_on_error(max_attempts=3, delay=1.0, backoff_factor=2.0)
        >>> def unstable_operation():
        ...     return external_api.call()

        >>> # 仅对特定异常重试
        >>> @retry_on_error(
        ...     max_attempts=5,
        ...     exception_class=(DataProviderError, ConnectionError)
        ... )
        >>> def fetch_stock_data(code):
        ...     return provider.get_daily_data(code)

        >>> # 静默重试（不记录日志）
        >>> @retry_on_error(max_attempts=3, log_retries=False)
        >>> def get_cache():
        ...     return cache.get("key")
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exception_class as e:
                    last_exception = e

                    if attempt < max_attempts:
                        # 计算延迟时间
                        wait_time = delay * (backoff_factor ** (attempt - 1))

                        if log_retries:
                            logger.warning(
                                f"{func.__name__} 执行失败，{wait_time:.1f}秒后重试 "
                                f"(第{attempt}/{max_attempts}次)",
                                exception=str(e),
                                attempt=attempt,
                                max_attempts=max_attempts
                            )

                        time.sleep(wait_time)
                    else:
                        # 最后一次尝试失败
                        if log_retries:
                            logger.error(
                                f"{func.__name__} 所有重试均失败 ({max_attempts}次)",
                                exception=str(e)
                            )

            # 所有重试均失败
            if reraise and last_exception:
                raise last_exception

            return None

        return wrapper  # type: ignore
    return decorator


def log_errors(
    log_level: str = "error",
    include_args: bool = False,
    include_traceback: bool = True
) -> Callable[[F], F]:
    """错误日志装饰器

    记录函数执行中的异常，但不捕获异常（总是重新抛出）。

    Args:
        log_level: 日志级别
        include_args: 是否在日志中包含函数参数
        include_traceback: 是否包含完整的调用栈

    Returns:
        装饰器函数

    Examples:
        >>> @log_errors()
        >>> def critical_operation():
        ...     # 异常会被记录并重新抛出
        ...     raise ValueError("Something went wrong")

        >>> @log_errors(include_args=True)
        >>> def process(data, config):
        ...     # 日志会包含 data 和 config 参数信息
        ...     return do_something(data, config)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_func = getattr(logger, log_level, logger.error)

                log_data = {
                    "function": func.__name__,
                    "exception_type": e.__class__.__name__,
                    "exception_message": str(e),
                }

                if include_args:
                    log_data["args"] = str(args)[:200]  # 限制长度
                    log_data["kwargs"] = str(kwargs)[:200]

                if include_traceback:
                    log_func(
                        f"{func.__name__} 抛出异常: {str(e)}",
                        **log_data,
                        exc_info=True
                    )
                else:
                    log_func(f"{func.__name__} 抛出异常: {str(e)}", **log_data)

                raise

        return wrapper  # type: ignore
    return decorator


def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    exception_class: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    log_error: bool = True,
    **kwargs
) -> Any:
    """安全执行函数

    执行函数并捕获异常，返回结果或默认值。这是一个函数（非装饰器），
    适合在需要临时安全执行某个操作的场景。

    Args:
        func: 要执行的函数
        *args: 函数的位置参数
        default_return: 发生异常时的默认返回值
        exception_class: 要捕获的异常类
        log_error: 是否记录错误日志
        **kwargs: 函数的关键字参数

    Returns:
        函数执行结果，或在异常时返回default_return

    Examples:
        >>> # 安全执行可能失败的操作
        >>> result = safe_execute(
        ...     provider.get_daily_data,
        ...     "000001",
        ...     default_return=pd.DataFrame()
        ... )

        >>> # 捕获特定异常
        >>> config = safe_execute(
        ...     load_config,
        ...     "/path/to/config.yaml",
        ...     exception_class=ConfigError,
        ...     default_return={}
        ... )

        >>> # 静默执行（不记录日志）
        >>> value = safe_execute(
        ...     cache.get,
        ...     "some_key",
        ...     log_error=False,
        ...     default_return=None
        ... )
    """
    try:
        return func(*args, **kwargs)
    except exception_class as e:
        if log_error:
            if isinstance(e, StockAnalysisError):
                logger.error(
                    f"safe_execute 执行 {func.__name__} 失败: {e.message}",
                    error_code=e.error_code,
                    **e.context
                )
            else:
                logger.error(f"safe_execute 执行 {func.__name__} 失败: {str(e)}")

        return default_return


def format_exception_message(exception: Exception) -> str:
    """格式化异常消息为易读的字符串

    Args:
        exception: 异常对象

    Returns:
        格式化的异常消息

    Examples:
        >>> try:
        ...     raise DataNotFoundError(
        ...         "数据不存在",
        ...         error_code="DATA_NOT_FOUND",
        ...         stock_code="000001"
        ...     )
        ... except Exception as e:
        ...     message = format_exception_message(e)
        ...     print(message)
        DataNotFoundError (DATA_NOT_FOUND): 数据不存在
        Context: stock_code=000001
    """
    if isinstance(exception, StockAnalysisError):
        lines = [
            f"{exception.__class__.__name__} ({exception.error_code}): {exception.message}"
        ]
        if exception.context:
            context_str = ", ".join(f"{k}={v}" for k, v in exception.context.items())
            lines.append(f"Context: {context_str}")
        return "\n".join(lines)
    else:
        return f"{exception.__class__.__name__}: {str(exception)}"


__all__ = [
    'handle_errors',
    'retry_on_error',
    'log_errors',
    'safe_execute',
    'format_exception_message',
]
