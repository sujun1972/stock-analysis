"""
每日指标同步任务

- sync_daily_basic_incremental_task：增量同步（委托 DailyBasicService.sync_incremental）
- sync_daily_basic_full_history_task：全量历史（委托 DailyBasicService.sync_full_history，支持 Redis 续继）

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.tasks.sync_tasks import _DummyContext


# ==================== 增量同步 ====================

@celery_app.task(
    bind=True,
    name="tasks.sync_daily_basic_incremental",
    max_retries=2,
    retry_backoff=180,
    retry_jitter=True,
)
def sync_daily_basic_incremental_task(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_strategy: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """
    每日指标增量同步（委托给 DailyBasicService.sync_incremental）。

    start_date / sync_strategy 均从 sync_configs 读取，
    也可由调用方显式传入覆盖。
    """
    from app.services.daily_basic_service import DailyBasicService

    logger.info(f"开始执行每日指标增量同步任务: strategy={sync_strategy} start_date={start_date} end_date={end_date}")

    service = DailyBasicService()
    result = run_async_in_celery(
        service.sync_incremental,
        start_date=start_date,
        end_date=end_date,
        sync_strategy=sync_strategy,
        max_requests_per_minute=max_requests_per_minute,
    )

    if result.get("status") == "success":
        logger.info(f"每日指标增量同步成功: {result.get('records', 0)} 条")
        return result
    else:
        error_msg = result.get('error', '未知错误')
        logger.warning(f"每日指标增量同步失败: {result}")
        raise Exception(f"同步失败: {error_msg}")


# ==================== 全量历史同步（续继） ====================

@celery_app.task(
    bind=True,
    name="tasks.sync_daily_basic_full_history",
    max_retries=0,
    soft_time_limit=28800,   # 8小时软超时
    time_limit=32400,        # 9小时硬超时
    acks_late=False,         # 支持续继，worker 重启后不自动重新入队
)
def sync_daily_basic_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 8,
    strategy: str = 'by_ts_code',
    max_requests_per_minute: Optional[int] = None,
):
    """全量历史每日指标同步（支持 Redis 续继，委托给 DailyBasicService）"""
    from app.core.redis_lock import redis_client, redis_lock
    from app.services.daily_basic_service import DailyBasicService

    logger.info(f"========== [Celery] 开始全量历史每日指标同步任务 strategy={strategy} concurrency={concurrency} ==========")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(DailyBasicService.FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("已有全量同步任务正在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = DailyBasicService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    concurrency=concurrency,
                    strategy=strategy,
                    update_state_fn=self.update_state,
                    max_requests_per_minute=max_requests_per_minute or 0,
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量历史每日指标同步结束: {result} ==========")
    return result
