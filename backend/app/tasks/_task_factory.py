"""Celery 任务工厂

消除增量/全量同步任务文件的样板代码。两个工厂函数：

- ``make_incremental_task``：生成"无参数 → sync_incremental，有参数 → 原始 sync_xxx"的增量任务
- ``make_full_history_task``：生成 redis_lock + 新 event loop + sync_full_history 的全量任务

LOCK_KEY 自动派生为 ``sync:{table_key}:full_history:lock``，与 ``sync_dashboard.release_stale_lock``
和 Service 类常量保持一致。Service 通过 ``service_path``（``module:Class``）懒加载，避免在 Celery
fork worker 顶层实例化触发连接池损坏。
"""

from __future__ import annotations

import asyncio
import importlib
import traceback
from typing import Any, Iterable, Optional, Tuple

from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


class _DummyContext:
    """无 Redis 时的占位 lock context."""

    def __enter__(self) -> bool:
        return True

    def __exit__(self, *args) -> None:
        pass


def _resolve_service(service_path: str) -> type:
    """``module:ClassName`` → class object，支持懒加载。"""
    module_path, _, cls_name = service_path.partition(":")
    if not cls_name:
        raise ValueError(f"service_path 必须为 'module:ClassName'，收到: {service_path!r}")
    module = importlib.import_module(module_path)
    return getattr(module, cls_name)


def _lock_key_for(table_key: str) -> str:
    """与 ``sync_dashboard.release_stale_lock`` 保持一致的派生规则。"""
    return f"sync:{table_key}:full_history:lock"


def make_incremental_task(
    *,
    name: str,
    service_path: str,
    display_name: str,
    raw_sync_method: str,
    raw_param_names: Iterable[str],
    raw_param_defaults: Optional[dict] = None,
    incremental_extra_kwargs: Optional[Iterable[str]] = None,
    max_retries: int = 0,
    retry_backoff: Optional[int] = None,
    retry_jitter: bool = False,
    soft_time_limit: Optional[int] = None,
    time_limit: Optional[int] = None,
):
    """生成增量同步 Celery 任务。

    Args:
        name: Celery 任务名（如 ``tasks.sync_cashflow``），必须与 ``sync_configs`` 一致。
        service_path: ``module:ClassName``，Service 类懒加载路径。
        display_name: 日志中使用的中文名称（如 "现金流量表"）。
        raw_sync_method: 有业务参数时调用的原始 sync 方法名（如 ``"sync_cashflow"``）。
        raw_param_names: 该任务接收的业务参数列表（按顺序），传给 raw_sync_method 作为关键字。
            任一非空时走 raw 路径；全部为空时走 ``sync_incremental``。
        incremental_extra_kwargs: 透传给 ``sync_incremental`` 的额外参数名（如
            ``("sync_strategy", "max_requests_per_minute")``），同时也透传给 raw 方法。
        max_retries / retry_backoff / retry_jitter / soft_time_limit / time_limit:
            Celery 任务装饰器选项，按需覆盖。
    """
    raw_param_names = tuple(raw_param_names)
    raw_defaults = dict(raw_param_defaults or {})
    extra_kwargs = tuple(incremental_extra_kwargs or ())

    task_options = {"bind": True, "name": name, "max_retries": max_retries}
    if retry_backoff is not None:
        task_options["retry_backoff"] = retry_backoff
    if retry_jitter:
        task_options["retry_jitter"] = retry_jitter
    if soft_time_limit is not None:
        task_options["soft_time_limit"] = soft_time_limit
    if time_limit is not None:
        task_options["time_limit"] = time_limit

    def task_impl(self, **kwargs):
        raw_args = {p: kwargs.get(p, raw_defaults.get(p)) for p in raw_param_names}
        extra_args = {p: kwargs.get(p) for p in extra_kwargs}

        log_parts = [f"{k}={v}" for k, v in {**raw_args, **extra_args}.items()]
        logger.info(f"开始执行{display_name}增量同步任务: {', '.join(log_parts)}")

        try:
            service_cls = _resolve_service(service_path)
            service = service_cls()

            # 判断是否真的有用户传入参数（区别于纯默认值）
            user_supplied = {
                p: kwargs.get(p) for p in raw_param_names
                if kwargs.get(p) not in (None, "")
            }
            has_raw_param = bool(user_supplied)

            if has_raw_param:
                method = getattr(service, raw_sync_method)
                result = run_async_in_celery(method, **raw_args, **extra_args)
            else:
                result = run_async_in_celery(service.sync_incremental, **extra_args)

            if result.get("status") == "success":
                logger.info(f"{display_name}增量同步成功: {result.get('records', 0)} 条")
                return result

            error_msg = result.get("error") or result.get("message") or "未知错误"
            logger.warning(f"{display_name}增量同步失败: {result}")
            raise Exception(f"同步失败: {error_msg}")

        except Exception as exc:
            logger.error(f"执行{display_name}增量同步任务失败: {exc}")
            logger.error(traceback.format_exc())
            raise

    task_impl.__name__ = f"{name.replace('.', '_')}_task"
    task_impl.__doc__ = (
        f"{display_name}增量同步任务（工厂生成）。\n\n"
        f"无业务参数时走 sync_incremental（从 sync_configs 读取回看天数）；\n"
        f"有业务参数时走 {raw_sync_method}（直接传 Tushare）。"
    )
    return celery_app.task(**task_options)(task_impl)


def make_full_history_task(
    *,
    name: str,
    service_path: str,
    table_key: str,
    display_name: str,
    soft_time_limit: int = 28800,
    time_limit: int = 32400,
    default_concurrency: int = 5,
    default_strategy: Optional[str] = None,
    accept_start_date_param: bool = True,
    accept_concurrency_param: bool = True,
    accept_strategy_param: bool = False,
    accept_max_rpm: bool = False,
    extra_kwargs: Optional[Iterable[Tuple[str, Any]]] = None,
    lock_key: Optional[str] = None,
):
    """生成全量历史同步 Celery 任务。

    Args:
        name: Celery 任务名（如 ``tasks.sync_cashflow_full_history``）。
        service_path: ``module:ClassName``，Service 类懒加载路径。
        table_key: 用于派生 lock_key（``sync:{table_key}:full_history:lock``），与
            ``sync_dashboard.FULL_SYNC_REDIS_KEYS`` / Service 类常量保持一致。
        display_name: 日志中使用的中文名称。
        soft_time_limit / time_limit: Celery 软/硬超时秒数。
        default_concurrency: 默认并发数。
        default_strategy: 当 ``accept_strategy_param=True`` 时的默认 strategy。
        accept_strategy_param: 是否接收 ``strategy`` 参数并透传给 ``sync_full_history``。
        accept_max_rpm: 是否接收 ``max_requests_per_minute`` 参数并透传。
        extra_kwargs: 额外固定参数 ``[(name, value), ...]``，每次调用透传给 ``sync_full_history``。
        lock_key: 显式指定 lock_key；不传则按 table_key 自动派生。
    """
    actual_lock_key = lock_key or _lock_key_for(table_key)
    extra_kwargs_tuple = tuple(extra_kwargs or ())

    task_options = {
        "bind": True,
        "name": name,
        "max_retries": 0,
        "soft_time_limit": soft_time_limit,
        "time_limit": time_limit,
        "acks_late": False,  # 支持 Redis 续继，worker 重启后不自动重新入队
    }

    def task_impl(
        self,
        start_date: Optional[str] = None,
        concurrency: Optional[int] = None,
        strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
        **_ignored,
    ):
        from app.core.redis_lock import redis_client, redis_lock

        effective_concurrency = concurrency if concurrency is not None else default_concurrency
        effective_strategy = strategy if strategy is not None else default_strategy

        logger.info(
            f"========== [Celery] 开始全量{display_name}同步任务 "
            f"start_date={start_date} concurrency={effective_concurrency} "
            f"strategy={effective_strategy} =========="
        )

        if redis_client is None:
            logger.error("Redis 不可用，无法执行全量同步任务")
            return {"status": "error", "message": "Redis 不可用"}

        lock_ctx = (
            redis_lock.acquire(actual_lock_key, timeout=soft_time_limit, blocking=False)
            if redis_lock else _DummyContext()
        )

        with lock_ctx as acquired:
            if not acquired and redis_lock:
                logger.warning(f"⚠️  全量{display_name}同步任务已在执行中，跳过本次执行")
                return {"status": "locked", "message": "已有全量同步任务正在进行"}

            service_cls = _resolve_service(service_path)
            service = service_cls()

            sync_kwargs = {
                "redis_client": redis_client,
                "update_state_fn": self.update_state,
            }
            if accept_start_date_param:
                sync_kwargs["start_date"] = start_date
            if accept_concurrency_param:
                sync_kwargs["concurrency"] = effective_concurrency
            if accept_strategy_param and effective_strategy is not None:
                sync_kwargs["strategy"] = effective_strategy
            if accept_max_rpm:
                sync_kwargs["max_requests_per_minute"] = (
                    max_requests_per_minute if max_requests_per_minute is not None else 0
                )
            for k, v in extra_kwargs_tuple:
                sync_kwargs.setdefault(k, v)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(service.sync_full_history(**sync_kwargs))
            finally:
                loop.close()

        logger.info(f"========== [Celery] 全量{display_name}同步结束: {result} ==========")
        return result

    task_impl.__name__ = f"{name.replace('.', '_')}_task"
    task_impl.__doc__ = (
        f"{display_name}全量历史同步任务（工厂生成）。\n\n"
        f"通过 Redis Set 记录已完成项实现中断续继，lock_key={actual_lock_key}。"
    )
    return celery_app.task(**task_options)(task_impl)
