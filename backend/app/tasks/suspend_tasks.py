"""
停复牌信息同步任务
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.suspend_service import (
    SuspendService,
    SUSPEND_FULL_HISTORY_LOCK_KEY,
)
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_suspend")
def sync_suspend_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    suspend_type: Optional[str] = None
):
    """
    同步停复牌信息数据（增量/单日）

    Args:
        ts_code: 股票代码（可输入多值，逗号分隔）
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        suspend_type: 停复牌类型，S-停牌，R-复牌
    """
    try:
        logger.info(f"开始执行停复牌信息同步任务: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}, suspend_type={suspend_type}")

        service = SuspendService()

        if not any([ts_code, trade_date, start_date, end_date, suspend_type]):
            result = run_async_in_celery(service.sync_incremental)
        else:
            result = run_async_in_celery(
                service.sync_suspend,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                suspend_type=suspend_type
            )

        if result["status"] == "success":
            logger.info(f"停复牌信息同步成功: {result['records']} 条")
            return result
        else:
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行停复牌信息同步任务失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_suspend_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_suspend_full_history_task(self, concurrency: int = 5):
    """
    按周切片全量同步停复牌历史数据（支持中断续继）

    不传 ts_code，按7天窗口拉全市场停复牌记录，历史峰值单周约4000条，
    安全低于 Tushare 5000条单次上限。5并发，约1100个周段。

    进度存储：Redis Set key = sync:suspend:full_history:progress
    中断后再次触发自动跳过已完成的周段，直到全部完成后清除进度记录。
    """
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量历史停复牌数据同步任务 concurrency={concurrency} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(SUSPEND_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量停复牌同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = SuspendService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    update_state_fn=self.update_state,
                    concurrency=concurrency
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量历史停复牌同步结束: {result} ==========")
    return result
