"""
重试策略模块

提供多种重试策略实现，包括：
- 指数退避
- 线性退避
- 固定延迟
- 带抖动的退避
"""

import time
import random
from abc import ABC, abstractmethod
from typing import Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetryMetrics:
    """重试指标统计"""

    function_name: str
    total_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    total_retry_time: float = 0.0
    last_attempt_at: Optional[datetime] = None
    last_error: Optional[str] = None
    retry_history: list = field(default_factory=list)

    def record_attempt(self, success: bool, duration: float, error: Optional[str] = None):
        """记录一次重试"""
        self.total_attempts += 1
        self.total_retry_time += duration
        self.last_attempt_at = datetime.now()

        if success:
            self.successful_retries += 1
        else:
            self.failed_retries += 1
            self.last_error = error

        self.retry_history.append({
            'timestamp': self.last_attempt_at,
            'success': success,
            'duration': duration,
            'error': error
        })

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'function_name': self.function_name,
            'total_attempts': self.total_attempts,
            'successful_retries': self.successful_retries,
            'failed_retries': self.failed_retries,
            'success_rate': self.successful_retries / max(1, self.total_attempts),
            'total_retry_time': self.total_retry_time,
            'average_retry_time': self.total_retry_time / max(1, self.total_attempts),
            'last_attempt_at': self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            'last_error': self.last_error
        }


class RetryStrategy(ABC):
    """重试策略抽象基类"""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """
        计算延迟时间

        Args:
            attempt: 当前尝试次数（从1开始）

        Returns:
            延迟秒数
        """
        pass


class FixedDelayStrategy(RetryStrategy):
    """固定延迟策略"""

    def __init__(self, delay: float = 1.0):
        """
        Args:
            delay: 固定延迟时间（秒）
        """
        self.delay = delay

    def get_delay(self, attempt: int) -> float:
        return self.delay


class LinearBackoffStrategy(RetryStrategy):
    """线性退避策略"""

    def __init__(self, base_delay: float = 1.0, increment: float = 1.0, max_delay: float = 60.0):
        """
        Args:
            base_delay: 基础延迟时间（秒）
            increment: 每次增加的延迟（秒）
            max_delay: 最大延迟时间（秒）
        """
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay + (attempt - 1) * self.increment
        return min(delay, self.max_delay)


class ExponentialBackoffStrategy(RetryStrategy):
    """指数退避策略"""

    def __init__(self, base_delay: float = 1.0, backoff_factor: float = 2.0, max_delay: float = 60.0):
        """
        Args:
            base_delay: 基础延迟时间（秒）
            backoff_factor: 退避系数
            max_delay: 最大延迟时间（秒）
        """
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


class JitteredBackoffStrategy(RetryStrategy):
    """带抖动的指数退避策略"""

    def __init__(
        self,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter_factor: float = 0.1
    ):
        """
        Args:
            base_delay: 基础延迟时间（秒）
            backoff_factor: 退避系数
            max_delay: 最大延迟时间（秒）
            jitter_factor: 抖动因子（0-1之间）
        """
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor

    def get_delay(self, attempt: int) -> float:
        # 计算基础延迟
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)

        # 添加随机抖动（±jitter_factor）
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        return max(0, delay + jitter)


class RetryContext:
    """重试上下文，用于在重试过程中传递信息"""

    def __init__(self, max_attempts: int, retry_budget: Optional[float] = None):
        """
        Args:
            max_attempts: 最大尝试次数
            retry_budget: 重试时间预算（秒），None表示无限制
        """
        self.max_attempts = max_attempts
        self.retry_budget = retry_budget
        self.attempt = 0
        self.start_time = time.time()
        self.total_delay = 0.0

    def can_retry(self) -> bool:
        """判断是否可以继续重试"""
        # 检查尝试次数
        if self.attempt >= self.max_attempts:
            return False

        # 检查时间预算
        if self.retry_budget is not None:
            elapsed = time.time() - self.start_time
            if elapsed + self.total_delay >= self.retry_budget:
                logger.warning(f"重试时间预算已用尽: {elapsed:.2f}s / {self.retry_budget}s")
                return False

        return True

    def record_delay(self, delay: float):
        """记录延迟时间"""
        self.total_delay += delay

    def next_attempt(self):
        """增加尝试次数"""
        self.attempt += 1


class RetryCondition:
    """重试条件判断器"""

    def __init__(
        self,
        retryable_exceptions: tuple = (Exception,),
        non_retryable_exceptions: tuple = (),
        custom_check: Optional[Callable[[Exception], bool]] = None
    ):
        """
        Args:
            retryable_exceptions: 可重试的异常类型
            non_retryable_exceptions: 不可重试的异常类型（优先级高）
            custom_check: 自定义检查函数，返回True表示可重试
        """
        self.retryable_exceptions = retryable_exceptions
        self.non_retryable_exceptions = non_retryable_exceptions
        self.custom_check = custom_check

    def should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试"""
        # 先检查不可重试异常
        if isinstance(exception, self.non_retryable_exceptions):
            return False

        # 检查可重试异常
        if not isinstance(exception, self.retryable_exceptions):
            return False

        # 自定义检查
        if self.custom_check is not None:
            return self.custom_check(exception)

        return True


class RetryCallback:
    """重试回调处理器"""

    def __init__(
        self,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        on_success: Optional[Callable[[int], None]] = None,
        on_failure: Optional[Callable[[Exception], None]] = None
    ):
        """
        Args:
            on_retry: 重试时的回调函数(attempt, exception, delay)
            on_success: 成功时的回调函数(total_attempts)
            on_failure: 最终失败时的回调函数(exception)
        """
        self.on_retry = on_retry
        self.on_success = on_success
        self.on_failure = on_failure

    def notify_retry(self, attempt: int, exception: Exception, delay: float):
        """通知重试"""
        if self.on_retry:
            try:
                self.on_retry(attempt, exception, delay)
            except Exception as e:
                logger.error(f"重试回调失败: {e}")

    def notify_success(self, total_attempts: int):
        """通知成功"""
        if self.on_success:
            try:
                self.on_success(total_attempts)
            except Exception as e:
                logger.error(f"成功回调失败: {e}")

    def notify_failure(self, exception: Exception):
        """通知失败"""
        if self.on_failure:
            try:
                self.on_failure(exception)
            except Exception as e:
                logger.error(f"失败回调失败: {e}")


# 全局重试指标收集器
_retry_metrics: dict[str, RetryMetrics] = {}


def get_retry_metrics(function_name: str) -> RetryMetrics:
    """获取指定函数的重试指标"""
    if function_name not in _retry_metrics:
        _retry_metrics[function_name] = RetryMetrics(function_name=function_name)
    return _retry_metrics[function_name]


def get_all_retry_metrics() -> dict[str, dict]:
    """获取所有重试指标"""
    return {name: metrics.get_stats() for name, metrics in _retry_metrics.items()}


def clear_retry_metrics():
    """清除所有重试指标"""
    _retry_metrics.clear()
