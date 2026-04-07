"""
股票回购同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_repurchase")
def sync_repurchase_task(
    self,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_strategy: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """增量同步股票回购数据"""
    try:
        logger.info(
            f"开始执行股票回购增量同步任务: strategy={sync_strategy} "
            f"ann_date={ann_date} start_date={start_date} end_date={end_date}"
        )

        from app.services.repurchase_service import RepurchaseService
        service = RepurchaseService()
        result = run_async_in_celery(
            service.sync_repurchase,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

        if result["status"] == "success":
            logger.info(f"股票回购同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"股票回购同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行股票回购同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_repurchase_full_history",
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_repurchase_full_history_task(
    self,
    start_date: str = None,
    concurrency: int = 5,
    strategy: str = 'by_month',
    max_requests_per_minute: Optional[int] = None,
):
    """全量同步股票回购历史数据（支持 Redis 续继，切片策略由 strategy 参数控制）

    repurchase 单次上限约1000条，按月切片避免截断，5并发。
    strategy: 'by_month'（按月，默认）、'by_week'（按7天窗口）、'by_date'（逐日）
    """
    from app.core.redis_lock import redis_client
    from app.services.repurchase_service import RepurchaseService

    logger.info(f"========== [Celery] 开始全量历史股票回购同步任务 strategy={strategy} concurrency={concurrency} ==========")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(RepurchaseService.FULL_HISTORY_LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = RepurchaseService()
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

    logger.info(f"========== [Celery] 全量历史股票回购同步结束: {result} ==========")
    return result
