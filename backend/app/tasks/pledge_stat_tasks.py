"""
股权质押统计同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.pledge_stat_service import PledgeStatService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_pledge_stat")
def sync_pledge_stat_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    sync_strategy: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """增量同步股权质押统计数据"""
    try:
        logger.info(
            f"开始执行股权质押统计增量同步任务: strategy={sync_strategy} "
            f"trade_date={trade_date} start_date={start_date} end_date={end_date} ts_code={ts_code}"
        )

        service = PledgeStatService()

        if not any([trade_date, start_date, end_date, ts_code]):
            result = run_async_in_celery(
                service.sync_incremental,
                sync_strategy=sync_strategy,
                max_requests_per_minute=max_requests_per_minute,
            )
        else:
            result = run_async_in_celery(
                service.sync_pledge_stat,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                sync_strategy=sync_strategy,
                max_requests_per_minute=max_requests_per_minute,
            )

        if result["status"] == "success":
            logger.info(f"股权质押统计同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"股权质押统计同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行股权质押统计同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_pledge_stat_full_history",
    max_retries=0,
    soft_time_limit=10800,
    time_limit=14400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_pledge_stat_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    strategy: str = 'by_ts_code',
    max_requests_per_minute: Optional[int] = None,
):
    """全量同步股权质押统计历史数据（支持中断续继，策略由 sync_configs 控制）"""
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量历史股权质押统计同步任务 concurrency={concurrency} ==========")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(PledgeStatService.FULL_HISTORY_LOCK_KEY, timeout=10800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = PledgeStatService()
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
                    max_requests_per_minute=max_requests_per_minute if max_requests_per_minute is not None else 0,
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量历史股权质押统计同步结束: {result} ==========")
    return result
