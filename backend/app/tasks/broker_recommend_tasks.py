"""
券商每月荐股同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_broker_recommend")
def sync_broker_recommend_task(
    self,
    month: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """
    同步券商每月荐股数据

    Args:
        month: 月度 YYYYMM（可选,不传则同步当前月）
        max_requests_per_minute: 限速（None=继承全局）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行券商荐股同步任务: month={month}")

        from app.services.broker_recommend_service import BrokerRecommendService
        service = BrokerRecommendService()

        if not month:
            result = run_async_in_celery(
                service.sync_incremental,
                max_requests_per_minute=max_requests_per_minute,
            )
        else:
            result = run_async_in_celery(
                service.sync_broker_recommend,
                month=month,
                max_requests_per_minute=max_requests_per_minute,
            )

        if result["status"] == "success":
            logger.info(f"券商荐股同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"券商荐股同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行券商荐股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_broker_recommend_full_history",
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,
)
def sync_broker_recommend_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    strategy: str = 'by_month_str',
    max_requests_per_minute: Optional[int] = None,
):
    """全量同步券商荐股历史数据（逐月请求，Redis Set 续继）"""
    from app.core.redis_lock import redis_client
    from app.core.redis_lock import redis_lock
    from app.tasks.sync_tasks import _DummyContext

    LOCK_KEY = 'sync:broker_recommend:full_history:lock'

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with (redis_lock.acquire(LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext()) as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        from app.services.broker_recommend_service import BrokerRecommendService
        service = BrokerRecommendService()
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
    return result
