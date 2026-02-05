"""
Circuit Breaker (熔断器) 实现
使用 pybreaker 库实现服务熔断，防止级联故障
"""

from typing import Any, Callable, Optional
from functools import wraps
import pybreaker
from loguru import logger


# 熔断器监听器：记录状态变化
class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    """熔断器事件监听器"""

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state, new_state):
        """熔断器状态变化时触发"""
        old_state_name = old_state.name if hasattr(old_state, "name") else str(old_state)
        new_state_name = new_state.name if hasattr(new_state, "name") else str(new_state)
        logger.warning(
            f"🔌 Circuit breaker state changed | "
            f"Name: {cb.name} | {old_state_name} → {new_state_name}"
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception):
        """请求失败时触发"""
        logger.error(
            f"❌ Circuit breaker failure | Name: {cb.name} | Error: {type(exc).__name__}: {exc}"
        )

    def success(self, cb: pybreaker.CircuitBreaker):
        """请求成功时触发"""
        logger.debug(f"✅ Circuit breaker success | Name: {cb.name}")


# 创建全局熔断器监听器
listener = CircuitBreakerListener()


# 数据库熔断器配置
db_breaker = pybreaker.CircuitBreaker(
    name="database",
    fail_max=5,  # 连续失败5次后打开熔断器
    reset_timeout=60,  # 熔断器打开后60秒尝试恢复
    exclude=[KeyError, ValueError],  # 这些异常不计入失败次数
    listeners=[listener],
)


# 外部API熔断器配置（更宽松）
external_api_breaker = pybreaker.CircuitBreaker(
    name="external_api",
    fail_max=10,  # 连续失败10次后打开
    reset_timeout=120,  # 熔断器打开后120秒尝试恢复
    listeners=[listener],
)


# Core服务熔断器配置
core_service_breaker = pybreaker.CircuitBreaker(
    name="core_service",
    fail_max=5,
    reset_timeout=60,
    listeners=[listener],
)


# Redis缓存熔断器配置
redis_breaker = pybreaker.CircuitBreaker(
    name="redis_cache",
    fail_max=3,  # 缓存失败更快熔断
    reset_timeout=30,  # 更短的恢复时间
    listeners=[listener],
)


def with_circuit_breaker(breaker: pybreaker.CircuitBreaker, fallback: Optional[Callable] = None):
    """
    熔断器装饰器

    Args:
        breaker: 要使用的熔断器实例
        fallback: 熔断时的降级函数（可选）

    Usage:
        @with_circuit_breaker(db_breaker)
        async def get_data():
            return await database.query()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                # 使用熔断器调用函数
                return await breaker.call_async(func, *args, **kwargs)
            except pybreaker.CircuitBreakerError as e:
                logger.error(
                    f"🔌 Circuit breaker open | Name: {breaker.name} | "
                    f"Function: {func.__name__} | State: {breaker.current_state}"
                )

                # 如果有降级函数，使用降级逻辑
                if fallback:
                    logger.info(f"↩️ Using fallback for {func.__name__}")
                    return await fallback(*args, **kwargs) if callable(fallback) else fallback

                # 否则抛出友好的错误
                raise ServiceUnavailableError(
                    f"服务 {breaker.name} 暂时不可用，请稍后再试"
                ) from e

        return wrapper

    return decorator


class ServiceUnavailableError(Exception):
    """服务不可用异常"""

    pass


# 便捷函数：重置熔断器
def reset_breaker(breaker: pybreaker.CircuitBreaker):
    """手动重置熔断器状态"""
    try:
        breaker.close()
        logger.info(f"🔧 Circuit breaker reset | Name: {breaker.name}")
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker {breaker.name}: {e}")


# 便捷函数：获取所有熔断器状态
def get_all_breakers_status() -> dict[str, dict[str, Any]]:
    """获取所有熔断器的状态"""
    breakers = {
        "database": db_breaker,
        "external_api": external_api_breaker,
        "core_service": core_service_breaker,
        "redis_cache": redis_breaker,
    }

    status = {}
    for name, breaker in breakers.items():
        status[name] = {
            "state": breaker.current_state,
            "fail_counter": breaker.fail_counter,
            "fail_max": breaker.fail_max,
            "reset_timeout": breaker._reset_timeout,
        }

    return status
