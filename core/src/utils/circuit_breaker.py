"""
断路器模式实现

提供Circuit Breaker模式，用于防止级联故障：
- CLOSED（关闭）：正常状态，请求正常通过
- OPEN（打开）：故障状态，快速失败
- HALF_OPEN（半开）：尝试恢复状态
"""

import time
from enum import Enum
from typing import Callable, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from threading import Lock
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CircuitState(Enum):
    """断路器状态"""
    CLOSED = "closed"  # 关闭状态，请求正常通过
    OPEN = "open"  # 打开状态，快速失败
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


@dataclass
class CircuitBreakerMetrics:
    """断路器指标"""
    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: Optional[datetime] = None
    state_transitions: list = field(default_factory=list)

    def record_success(self):
        """记录成功调用"""
        self.success_count += 1
        self.total_calls += 1

    def record_failure(self):
        """记录失败调用"""
        self.failure_count += 1
        self.total_calls += 1
        self.last_failure_time = datetime.now()

    def change_state(self, new_state: CircuitState):
        """改变状态"""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            self.last_state_change = datetime.now()
            self.state_transitions.append({
                'from': old_state.value,
                'to': new_state.value,
                'timestamp': self.last_state_change
            })
            logger.info(f"断路器 {self.name} 状态变更: {old_state.value} -> {new_state.value}")

    def reset_counts(self):
        """重置计数器"""
        self.failure_count = 0
        self.success_count = 0

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_calls': self.total_calls,
            'failure_rate': self.failure_count / max(1, self.total_calls),
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_state_change': self.last_state_change.isoformat() if self.last_state_change else None,
            'state_transitions_count': len(self.state_transitions)
        }


class CircuitBreakerError(Exception):
    """断路器打开异常"""

    def __init__(self, message: str, breaker_name: str):
        super().__init__(message)
        self.breaker_name = breaker_name


class CircuitBreaker:
    """
    断路器实现

    工作原理：
    1. CLOSED状态：正常工作，记录失败次数
    2. 失败次数达到阈值 -> 进入OPEN状态
    3. OPEN状态：直接拒绝请求，等待恢复超时
    4. 恢复超时后 -> 进入HALF_OPEN状态
    5. HALF_OPEN状态：允许少量请求通过
       - 如果成功 -> 回到CLOSED状态
       - 如果失败 -> 回到OPEN状态
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        初始化断路器

        Args:
            name: 断路器名称
            failure_threshold: 失败阈值，连续失败这么多次后打开断路器
            recovery_timeout: 恢复超时时间（秒），打开后等待这么久尝试恢复
            half_open_max_calls: 半开状态最大允许调用次数
            expected_exceptions: 期望捕获的异常类型
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions

        self.metrics = CircuitBreakerMetrics(name=name)
        self._lock = Lock()
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        return self.metrics.state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过断路器调用函数

        Args:
            func: 要调用的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值

        Raises:
            CircuitBreakerError: 断路器打开时抛出
            Exception: 函数执行时的异常
        """
        with self._lock:
            # 检查是否可以调用
            if not self._can_call():
                raise CircuitBreakerError(
                    f"断路器 {self.name} 已打开，拒绝调用",
                    breaker_name=self.name
                )

            # 尝试调用函数
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exceptions as e:
                self._on_failure()
                raise

    def _can_call(self) -> bool:
        """检查是否可以调用"""
        current_state = self.metrics.state

        if current_state == CircuitState.CLOSED:
            return True

        if current_state == CircuitState.OPEN:
            # 检查是否可以进入半开状态
            if self._should_attempt_reset():
                self.metrics.change_state(CircuitState.HALF_OPEN)
                self._half_open_calls = 0
                return True
            return False

        if current_state == CircuitState.HALF_OPEN:
            # 半开状态下，限制调用次数
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

        return False

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置（从OPEN到HALF_OPEN）"""
        if self._last_failure_time is None:
            return True

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.recovery_timeout

    def _on_success(self):
        """成功时的处理"""
        self.metrics.record_success()

        if self.metrics.state == CircuitState.HALF_OPEN:
            # 半开状态成功 -> 关闭断路器
            logger.info(f"断路器 {self.name} 恢复正常")
            self.metrics.change_state(CircuitState.CLOSED)
            self.metrics.reset_counts()
            self._half_open_calls = 0

        elif self.metrics.state == CircuitState.CLOSED:
            # 关闭状态成功 -> 重置失败计数
            if self.metrics.failure_count > 0:
                self.metrics.reset_counts()

    def _on_failure(self):
        """失败时的处理"""
        self.metrics.record_failure()
        self._last_failure_time = time.time()

        if self.metrics.state == CircuitState.HALF_OPEN:
            # 半开状态失败 -> 重新打开断路器
            logger.warning(f"断路器 {self.name} 恢复失败，重新打开")
            self.metrics.change_state(CircuitState.OPEN)
            self._half_open_calls = 0

        elif self.metrics.state == CircuitState.CLOSED:
            # 关闭状态失败 -> 检查是否达到阈值
            if self.metrics.failure_count >= self.failure_threshold:
                logger.warning(
                    f"断路器 {self.name} 失败次数达到阈值 "
                    f"({self.metrics.failure_count}/{self.failure_threshold})，打开断路器"
                )
                self.metrics.change_state(CircuitState.OPEN)

    def reset(self):
        """手动重置断路器"""
        with self._lock:
            logger.info(f"手动重置断路器 {self.name}")
            self.metrics.change_state(CircuitState.CLOSED)
            self.metrics.reset_counts()
            self._last_failure_time = None
            self._half_open_calls = 0

    def force_open(self):
        """手动打开断路器"""
        with self._lock:
            logger.warning(f"手动打开断路器 {self.name}")
            self.metrics.change_state(CircuitState.OPEN)
            self._last_failure_time = time.time()

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.metrics.get_stats()


class CircuitBreakerManager:
    """断路器管理器，管理多个断路器实例"""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        expected_exceptions: tuple = (Exception,)
    ) -> CircuitBreaker:
        """
        获取或创建断路器

        Args:
            name: 断路器名称
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时
            half_open_max_calls: 半开状态最大调用次数
            expected_exceptions: 期望异常类型

        Returns:
            断路器实例
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    half_open_max_calls=half_open_max_calls,
                    expected_exceptions=expected_exceptions
                )
            return self._breakers[name]

    def remove_breaker(self, name: str):
        """移除断路器"""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]

    def reset_all(self):
        """重置所有断路器"""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()

    def get_all_stats(self) -> dict[str, dict]:
        """获取所有断路器的统计信息"""
        with self._lock:
            return {name: breaker.get_stats() for name, breaker in self._breakers.items()}


# 全局断路器管理器
_global_breaker_manager = CircuitBreakerManager()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    half_open_max_calls: int = 3,
    expected_exceptions: tuple = (Exception,)
) -> CircuitBreaker:
    """获取全局断路器实例"""
    return _global_breaker_manager.get_breaker(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
        expected_exceptions=expected_exceptions
    )


def get_all_circuit_breaker_stats() -> dict[str, dict]:
    """获取所有断路器的统计信息"""
    return _global_breaker_manager.get_all_stats()


def reset_all_circuit_breakers():
    """重置所有断路器"""
    _global_breaker_manager.reset_all()
