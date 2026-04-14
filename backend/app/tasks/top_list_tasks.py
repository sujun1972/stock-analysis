"""
龙虎榜每日明细 Celery 任务
"""
import asyncio
from typing import Optional
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.top_list_service import TopListService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_top_list")
def sync_top_list_task(
    self,
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None
):
    """
    同步龙虎榜每日明细数据

    Args:
        trade_date: 交易日期，格式：YYYYMMDD（可选，默认为当天）
        ts_code: 股票代码（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行龙虎榜数据同步任务: trade_date={trade_date}, ts_code={ts_code}")

        # 使用辅助函数运行异步代码
        service = TopListService()
        if not any([trade_date, ts_code]):
            result = run_async_in_celery(service.sync_incremental)
        else:
            result = run_async_in_celery(
                service.sync_top_list,
                trade_date=trade_date,
                ts_code=ts_code
            )

        logger.info(f"龙虎榜数据同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"龙虎榜数据同步任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_top_list_full_history",
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,
)
def sync_top_list_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    **kwargs
):
    """按自然月切片全量同步龙虎榜每日明细历史数据（支持中断续继）"""
    from app.core.redis_lock import redis_client, redis_lock
    from app.tasks.sync_tasks import _DummyContext

    LOCK_KEY = "sync:top_list:full_history:lock"
    logger.info(f"[Celery] 开始龙虎榜全量历史同步 start_date={start_date} concurrency={concurrency}")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = TopListService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    concurrency=concurrency,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(f"[Celery] 龙虎榜全量历史同步结束: 成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')}")
    return result
