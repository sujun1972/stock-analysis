"""
实用装饰器

提供性能监控、缓存、重试等功能
"""

import time
import functools
from typing import Callable, Any, Optional
from src.utils.logger import get_logger
from src.utils.retry_strategy import (
    RetryStrategy,
    ExponentialBackoffStrategy,
    JitteredBackoffStrategy,
    RetryContext,
    RetryCondition,
    RetryCallback,
    get_retry_metrics
)
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerError, get_circuit_breaker

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
    重试装饰器 - 失败时自动重试（简单版本，保持向后兼容）

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


def retry_enhanced(
    max_attempts: int = 3,
    strategy: Optional[RetryStrategy] = None,
    retry_budget: Optional[float] = None,
    retryable_exceptions: tuple = (Exception,),
    non_retryable_exceptions: tuple = (),
    use_circuit_breaker: bool = False,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 60.0,
    collect_metrics: bool = True,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    on_success: Optional[Callable[[int], None]] = None,
    on_failure: Optional[Callable[[Exception], None]] = None
):
    """
    增强版重试装饰器 - 支持多种重试策略、断路器、指标收集

    Args:
        max_attempts: 最大尝试次数
        strategy: 重试策略，默认使用抖动指数退避
        retry_budget: 重试时间预算（秒），None表示无限制
        retryable_exceptions: 可重试的异常类型
        non_retryable_exceptions: 不可重试的异常类型（优先级高）
        use_circuit_breaker: 是否使用断路器
        circuit_breaker_name: 断路器名称（默认使用函数名）
        circuit_breaker_threshold: 断路器失败阈值
        circuit_breaker_timeout: 断路器恢复超时（秒）
        collect_metrics: 是否收集重试指标
        on_retry: 重试时的回调函数
        on_success: 成功时的回调函数
        on_failure: 最终失败时的回调函数

    Example:
        @retry_enhanced(
            max_attempts=5,
            strategy=JitteredBackoffStrategy(base_delay=1.0, backoff_factor=2.0),
            retry_budget=300,
            use_circuit_breaker=True,
            collect_metrics=True
        )
        def fetch_data_from_api(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # 默认策略
        retry_strategy = strategy or JitteredBackoffStrategy(
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0,
            jitter_factor=0.1
        )

        # 重试条件
        retry_condition = RetryCondition(
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions
        )

        # 回调处理器
        retry_callback = RetryCallback(
            on_retry=on_retry,
            on_success=on_success,
            on_failure=on_failure
        )

        # 断路器
        breaker = None
        if use_circuit_breaker:
            breaker_name = circuit_breaker_name or f"breaker_{func.__name__}"
            breaker = get_circuit_breaker(
                name=breaker_name,
                failure_threshold=circuit_breaker_threshold,
                recovery_timeout=circuit_breaker_timeout,
                expected_exceptions=retryable_exceptions
            )

        # 指标收集
        metrics = None
        if collect_metrics:
            metrics = get_retry_metrics(func.__name__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 创建重试上下文
            context = RetryContext(
                max_attempts=max_attempts,
                retry_budget=retry_budget
            )

            last_exception = None
            start_time = time.time()

            while context.can_retry():
                context.next_attempt()
                attempt = context.attempt

                try:
                    # 如果使用断路器，通过断路器调用
                    if breaker:
                        result = breaker.call(func, *args, **kwargs)
                    else:
                        result = func(*args, **kwargs)

                    # 成功
                    if metrics:
                        metrics.record_attempt(
                            success=True,
                            duration=time.time() - start_time
                        )

                    retry_callback.notify_success(attempt)
                    return result

                except CircuitBreakerError:
                    # 断路器打开，直接抛出
                    logger.error(f"{func.__name__} 断路器已打开，停止重试")
                    raise

                except Exception as e:
                    last_exception = e

                    # 检查是否应该重试
                    if not retry_condition.should_retry(e):
                        logger.error(f"{func.__name__} 遇到不可重试异常: {type(e).__name__}")
                        if metrics:
                            metrics.record_attempt(
                                success=False,
                                duration=time.time() - start_time,
                                error=str(e)
                            )
                        retry_callback.notify_failure(e)
                        raise

                    # 最后一次尝试失败
                    if not context.can_retry():
                        logger.error(
                            f"{func.__name__} 失败 (尝试 {attempt}/{max_attempts}): {e}"
                        )
                        if metrics:
                            metrics.record_attempt(
                                success=False,
                                duration=time.time() - start_time,
                                error=str(e)
                            )
                        retry_callback.notify_failure(e)
                        raise

                    # 计算延迟并等待
                    delay = retry_strategy.get_delay(attempt)
                    context.record_delay(delay)

                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt}/{max_attempts}), "
                        f"{delay:.2f}秒后重试: {e}"
                    )

                    retry_callback.notify_retry(attempt, e, delay)
                    time.sleep(delay)

            # 不应到达这里
            if metrics:
                metrics.record_attempt(
                    success=False,
                    duration=time.time() - start_time,
                    error=str(last_exception) if last_exception else "Unknown"
                )
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} 重试失败")

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
