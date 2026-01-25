"""
实用装饰器

提供性能监控、缓存、重试等功能
"""

import time
import functools
from typing import Callable, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def timer(func: Callable) -> Callable:
    """
    计时装饰器 - 记录函数执行时间

    Example:
        @timer
        def train_model(...):
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time

        # 格式化时间显示
        if elapsed < 1:
            time_str = f"{elapsed*1000:.2f}ms"
        elif elapsed < 60:
            time_str = f"{elapsed:.2f}s"
        else:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            time_str = f"{minutes}m {seconds:.2f}s"

        logger.info(f"{func.__name__} 执行耗时: {time_str}")
        return result

    return wrapper


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器 - 失败时自动重试

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数（每次重试延迟时间乘以此系数）
        exceptions: 需要重试的异常类型

    Example:
        @retry(max_attempts=3, delay=1.0)
        def fetch_data_from_api(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} 失败 (尝试 {attempt}/{max_attempts}): {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt}/{max_attempts}), "
                        f"{current_delay:.1f}秒后重试: {e}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            # 不应到达这里，但为了类型检查
            raise last_exception

        return wrapper
    return decorator


def cache_result(ttl: Optional[int] = None):
    """
    缓存装饰器 - 缓存函数结果（简单版本）

    Args:
        ttl: 缓存过期时间（秒），None 表示永不过期

    Example:
        @cache_result(ttl=3600)
        def compute_features(...):
            ...

    Note:
        此装饰器适用于纯函数，不适合有副作用的函数
    """
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_time = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))

            # 检查缓存是否过期
            if ttl is not None and key in cache_time:
                if time.time() - cache_time[key] > ttl:
                    logger.debug(f"{func.__name__} 缓存过期，重新计算")
                    del cache[key]
                    del cache_time[key]

            # 返回缓存或计算新值
            if key in cache:
                logger.debug(f"{func.__name__} 使用缓存结果")
                return cache[key]

            logger.debug(f"{func.__name__} 计算新结果并缓存")
            result = func(*args, **kwargs)
            cache[key] = result
            cache_time[key] = time.time()
            return result

        # 添加清除缓存的方法
        def clear_cache():
            cache.clear()
            cache_time.clear()
            logger.info(f"{func.__name__} 缓存已清除")

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator


def validate_args(**validators):
    """
    参数验证装饰器

    Args:
        **validators: 参数名到验证函数的映射

    Example:
        @validate_args(
            symbol=lambda x: len(x) == 6,
            period=lambda x: x > 0
        )
        def fetch_data(symbol: str, period: int):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数参数名
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # 验证参数
            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if not validator(value):
                        raise ValueError(
                            f"参数 '{param_name}' 验证失败: {value}"
                        )

            return func(*args, **kwargs)

        return wrapper
    return decorator
