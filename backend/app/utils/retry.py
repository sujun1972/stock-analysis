"""
重试逻辑工具模块
提供异步和同步重试功能
"""

import asyncio
from typing import Callable, Any, Optional, Type
from loguru import logger


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    delay_base: float = 3.0,
    delay_strategy: str = 'linear',
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    异步函数重试包装器

    Args:
        func: 要执行的异步函数
        *args: 函数的位置参数
        max_retries: 最大重试次数（默认3次）
        delay_base: 基础延迟时间（秒，默认3.0）
        delay_strategy: 延迟策略
            - 'linear': 线性增长 (delay_base * retry_count)
            - 'exponential': 指数增长 (delay_base ** retry_count)
            - 'constant': 固定延迟 (delay_base)
        exceptions: 需要重试的异常类型元组（默认所有Exception）
        on_retry: 重试时的回调函数，接收参数 (retry_count, max_retries, error)
        **kwargs: 函数的关键字参数

    Returns:
        函数执行结果

    Raises:
        最后一次执行的异常（如果所有重试都失败）

    Examples:
        >>> async def fetch_data():
        ...     # 可能失败的异步操作
        ...     pass
        >>> result = await retry_async(fetch_data, max_retries=5)

        >>> async def save_data(data):
        ...     # 保存数据
        ...     pass
        >>> result = await retry_async(
        ...     save_data,
        ...     {"value": 123},
        ...     max_retries=3,
        ...     delay_strategy='exponential'
        ... )
    """
    last_error = None

    for retry_count in range(1, max_retries + 1):
        try:
            # 执行函数
            return await func(*args, **kwargs)

        except exceptions as e:
            last_error = e

            # 如果是最后一次尝试，直接抛出异常
            if retry_count >= max_retries:
                logger.error(f"重试失败，已达到最大重试次数 {max_retries}: {e}")
                raise

            # 计算延迟时间
            if delay_strategy == 'linear':
                delay = delay_base * retry_count
            elif delay_strategy == 'exponential':
                delay = delay_base ** retry_count
            elif delay_strategy == 'constant':
                delay = delay_base
            else:
                delay = delay_base * retry_count  # 默认线性

            logger.warning(
                f"执行失败 (尝试 {retry_count}/{max_retries})，"
                f"{delay:.1f}秒后重试 | 异常类型: {type(e).__name__} | 错误: {e}"
            )

            # 调用重试回调
            if on_retry:
                try:
                    await on_retry(retry_count, max_retries, e)
                except Exception as callback_error:
                    # 回调函数执行失败不应影响重试逻辑，记录错误但继续
                    logger.error(
                        f"重试回调函数执行失败 | "
                        f"回调错误类型: {type(callback_error).__name__} | "
                        f"错误: {callback_error}"
                    )

            # 等待后重试
            await asyncio.sleep(delay)

    # 理论上不会到达这里，但为了类型检查完整性
    if last_error:
        raise last_error
    raise Exception("未知错误：重试逻辑异常")


def retry_sync(
    func: Callable,
    *args,
    max_retries: int = 3,
    delay_base: float = 3.0,
    delay_strategy: str = 'linear',
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    同步函数重试包装器

    Args:
        func: 要执行的同步函数
        *args: 函数的位置参数
        max_retries: 最大重试次数（默认3次）
        delay_base: 基础延迟时间（秒，默认3.0）
        delay_strategy: 延迟策略
            - 'linear': 线性增长 (delay_base * retry_count)
            - 'exponential': 指数增长 (delay_base ** retry_count)
            - 'constant': 固定延迟 (delay_base)
        exceptions: 需要重试的异常类型元组（默认所有Exception）
        on_retry: 重试时的回调函数，接收参数 (retry_count, max_retries, error)
        **kwargs: 函数的关键字参数

    Returns:
        函数执行结果

    Raises:
        最后一次执行的异常（如果所有重试都失败）

    Examples:
        >>> def fetch_data():
        ...     # 可能失败的操作
        ...     pass
        >>> result = retry_sync(fetch_data, max_retries=5)
    """
    import time

    last_error = None

    for retry_count in range(1, max_retries + 1):
        try:
            # 执行函数
            return func(*args, **kwargs)

        except exceptions as e:
            last_error = e

            # 如果是最后一次尝试，直接抛出异常
            if retry_count >= max_retries:
                logger.error(f"重试失败，已达到最大重试次数 {max_retries}: {e}")
                raise

            # 计算延迟时间
            if delay_strategy == 'linear':
                delay = delay_base * retry_count
            elif delay_strategy == 'exponential':
                delay = delay_base ** retry_count
            elif delay_strategy == 'constant':
                delay = delay_base
            else:
                delay = delay_base * retry_count  # 默认线性

            logger.warning(
                f"执行失败 (尝试 {retry_count}/{max_retries})，"
                f"{delay:.1f}秒后重试 | 异常类型: {type(e).__name__} | 错误: {e}"
            )

            # 调用重试回调
            if on_retry:
                try:
                    on_retry(retry_count, max_retries, e)
                except Exception as callback_error:
                    # 回调函数执行失败不应影响重试逻辑，记录错误但继续
                    logger.error(
                        f"重试回调函数执行失败 | "
                        f"回调错误类型: {type(callback_error).__name__} | "
                        f"错误: {callback_error}"
                    )

            # 等待后重试
            time.sleep(delay)

    # 理论上不会到达这里，但为了类型检查完整性
    if last_error:
        raise last_error
    raise Exception("未知错误：重试逻辑异常")
