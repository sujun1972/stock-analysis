"""
复权因子数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.adj_factor_service import AdjFactorService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_adj_factor")
def sync_adj_factor_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_strategy: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """增量同步复权因子数据"""
    try:
        logger.info(
            f"开始执行复权因子增量同步任务: strategy={sync_strategy} "
            f"ts_code={ts_code} start_date={start_date} end_date={end_date}"
        )

        service = AdjFactorService()
        result = run_async_in_celery(
            service.sync_incremental,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

        if result["status"] == "success":
            logger.info(f"复权因子增量同步成功: {result.get('records', 0)} 条")
            return result
        else:
            logger.warning(f"复权因子增量同步失败: {result}")
            raise Exception(f"同步失败: {result.get('error', '未知错误')}")

    except Exception as e:
        logger.error(f"执行复权因子增量同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_adj_factor_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_adj_factor_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 8,
    strategy: str = 'by_ts_code',
    max_requests_per_minute: Optional[int] = None,
):
    """全量历史复权因子同步（支持 Redis 续继，委托给 AdjFactorService）"""
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始复权因子全量历史同步任务 strategy={strategy} concurrency={concurrency} ==========")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(AdjFactorService.FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  复权因子全量同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = AdjFactorService()
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

    logger.info(f"========== [Celery] 复权因子全量历史同步结束: {result} ==========")
    return result
