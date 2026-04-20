"""
AkShareRetryDecorator — Service 层的指数退避重试装饰器。

与 Provider 层重试的分工：
  - `core/src/providers/akshare/api_client.py::AkShareAPIClient.execute` 处理 AkShare
    库级调用（Provider 方法已自动带上）。
  - 本装饰器用于 Service 自己做的非 Provider 请求（典型：`anns_content_fetcher` 的
    PDF/HTML 抓取），以及 Phase 2+ 计划中直连第三方站点的爬虫。

三态分类：
  - rate_limit：出现"限流 / 429 / 403"等关键字 → 立即抛 `AkShareRateLimitError`，不重试
  - transient：超时 / 连接错误 / 5xx → 指数退避重试
  - permanent：其余（数据格式异常、字段缺失）→ 原样抛出，不重试

耗尽重试后抛 `AkShareRetryExhaustedError` 并记 `logger.error`，便于 hook 到告警。
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import random
import time
from typing import Any, Callable, Iterable, Optional, Tuple, TypeVar

from app.core.logging_config import get_logger

logger = get_logger()

F = TypeVar('F', bound=Callable[..., Any])


class AkShareRateLimitError(Exception):
    """AkShare / 爬虫触发限流。调用方应暂停较长时间再试。"""


class AkShareRetryExhaustedError(Exception):
    """指数退避耗尽仍失败。"""


# 异常消息中出现即判定为远端限流，遇到即终止
_RATE_LIMIT_KEYWORDS: Tuple[str, ...] = (
    '访问频繁', '访问过于频繁', '请求过于频繁',
    '限流', '限速', '速率限制',
    'rate limit', 'ratelimit', 'too many requests', '429',
    '403 forbidden',
)

# 异常消息中出现即判定为瞬时失败，可重试
_TRANSIENT_KEYWORDS: Tuple[str, ...] = (
    'timeout', '超时',
    'connection', 'connection reset', 'connection refused', 'connectionerror',
    'network', '网络',
    'remotedisconnected', 'protocolerror',
    'httperror', 'readtimeout', 'connecttimeout',
    '502', '503', '504',
)


def _classify(exc: BaseException) -> str:
    """把异常归为 'rate_limit' / 'transient' / 'permanent'。"""
    msg = (str(exc) or exc.__class__.__name__).lower()
    if any(kw.lower() in msg for kw in _RATE_LIMIT_KEYWORDS):
        return 'rate_limit'
    if any(kw.lower() in msg for kw in _TRANSIENT_KEYWORDS):
        return 'transient'
    return 'permanent'


def _compute_delay(attempt: int, base: float, cap: float) -> float:
    """指数退避 + 10% jitter（避免惊群）。"""
    delay = min(base * (2 ** attempt), cap)
    return delay + random.uniform(0, delay * 0.1)


class AkShareRetryDecorator:
    """
    指数退避重试装饰器。用法：

        @AkShareRetryDecorator(max_retries=3, base_delay=2.0)
        def fetch(url): ...

        @AkShareRetryDecorator()
        async def fetch_async(url): ...

    Args:
        max_retries: 重试次数（不含首次），默认 3
        base_delay:  首次重试等待秒数，第 n 次 = base * 2^(n-1) + jitter；默认 2.0
        max_delay:   单次等待上限（防指数爆炸），默认 30.0
        transient_exceptions: 强制视为瞬时失败的异常类型（与关键字匹配合并）
        rate_limit_cooldown: 限流时打日志的建议冷却秒数；装饰器本身不 sleep
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        transient_exceptions: Optional[Iterable[type]] = None,
        rate_limit_cooldown: int = 60,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries 不能为负")
        if base_delay <= 0 or max_delay <= 0:
            raise ValueError("base_delay / max_delay 必须为正")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.transient_exceptions: Tuple[type, ...] = tuple(transient_exceptions or ())
        self.rate_limit_cooldown = rate_limit_cooldown

    def __call__(self, func: F) -> F:
        return self.wrap(func)

    def wrap(self, func: F) -> F:
        """同步和异步通用入口。返回同类型 wrapper。"""
        if inspect.iscoroutinefunction(func):
            return self._wrap_async(func)  # type: ignore[return-value]
        return self._wrap_sync(func)

    # ---------- 内部：把捕获的异常决策为"重试 / 限流抛出 / 原样抛出"三选一 ----------

    def _handle_exc(
        self,
        exc: BaseException,
        attempt: int,
        name: str,
    ) -> Optional[float]:
        """根据异常分类决定下一步：

        Returns:
            float — 需要等待的秒数后重试
            None  — 本轮逻辑已处理完毕（抛 rate_limit / permanent / 耗尽），调用方 break

        副作用：会抛 `AkShareRateLimitError` / `exc` 本身（permanent）/
        `AkShareRetryExhaustedError`（耗尽）。
        """
        kind = (
            'transient' if isinstance(exc, self.transient_exceptions) else _classify(exc)
        )

        if kind == 'rate_limit':
            logger.warning(
                f"[AkShareRetry] {name} 触发限流，停止重试；建议暂停 {self.rate_limit_cooldown}s：{exc}"
            )
            raise AkShareRateLimitError(f"{name}: {exc}") from exc

        if kind == 'permanent':
            logger.warning(f"[AkShareRetry] {name} 非瞬时失败，停止重试：{exc}")
            raise exc

        # transient：还有重试机会则返回等待秒数，否则抛耗尽
        if attempt < self.max_retries:
            delay = _compute_delay(attempt, self.base_delay, self.max_delay)
            logger.info(
                f"[AkShareRetry] {name} 第 {attempt + 1}/{self.max_retries} 次失败，"
                f"{delay:.1f}s 后重试：{exc}"
            )
            return delay

        logger.error(
            f"[AkShareRetry] {name} 重试 {self.max_retries} 次后仍失败：{exc}"
        )
        raise AkShareRetryExhaustedError(
            f"{name} 重试 {self.max_retries} 次后仍失败: {exc}"
        ) from exc

    # ---------- 同步 / 异步 wrapper（差异仅在调用和 sleep） ----------

    def _wrap_sync(self, func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = getattr(func, '__qualname__', getattr(func, '__name__', str(func)))
            for attempt in range(self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001  — 需捕获全部以做分类
                    delay = self._handle_exc(e, attempt, name)
                # 只有 transient 且未耗尽才会 fall through
                time.sleep(delay)
            # 理论不可达（_handle_exc 在耗尽时已抛 AkShareRetryExhaustedError）
            raise AkShareRetryExhaustedError(f"{name} 重试流程异常终止")

        return wrapper  # type: ignore[return-value]

    def _wrap_async(self, func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = getattr(func, '__qualname__', getattr(func, '__name__', str(func)))
            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    delay = self._handle_exc(e, attempt, name)
                await asyncio.sleep(delay)
            raise AkShareRetryExhaustedError(f"{name} 重试流程异常终止")

        return wrapper  # type: ignore[return-value]


__all__ = [
    'AkShareRetryDecorator',
    'AkShareRateLimitError',
    'AkShareRetryExhaustedError',
]
