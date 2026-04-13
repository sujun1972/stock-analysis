"""
港股通十大成交股数据同步任务
"""

import asyncio

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.ggt_top10_service import GgtTop10Service
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_ggt_top10")
def sync_ggt_top10_task(
    self,
    ts_code: str = None,
    trade_date: str = None,
    start_date: str = None,
    end_date: str = None,
    market_type: str = None
):
    """
    同步港股通十大成交股数据

    无参数调用时使用 sync_incremental（从 sync_configs 读取回看天数，逐交易日同步）。
    有参数时使用原始 sync_ggt_top10（直接传参给 Tushare）。
    """
    try:
        logger.info(f"开始执行港股通十大成交股同步任务: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

        service = GgtTop10Service()

        # 无参数时走增量同步（从 sync_configs 读取配置，逐交易日）
        if not ts_code and not trade_date and not start_date and not end_date and not market_type:
            result = run_async_in_celery(service.sync_incremental)
        else:
            result = run_async_in_celery(
                service.sync_ggt_top10,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                market_type=market_type
            )

        if result.get("status") == "success":
            logger.info(f"港股通十大成交股同步成功: {result.get('records', 0)} 条")
            return result
        else:
            error_msg = result.get('error', '未知错误')
            logger.warning(f"港股通十大成交股同步失败: {result}")
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"港股通十大成交股同步任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_ggt_top10_full_history",
    max_retries=0,
    soft_time_limit=14400,
    time_limit=18000,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_ggt_top10_full_history_task(self, start_date: str = None, concurrency: int = 10):
    """
    逐交易日全量同步港股通十大成交股历史数据（支持中断续继）

    ggt_top10 接口只支持 trade_date 单日查询，每日约 20 条。
    10 并发，约 2700+ 个交易日（2015年起）。

    Args:
        start_date: 同步起始日期 YYYYMMDD，不传则从 2015-01-01 开始

    进度存储：Redis Set key = sync:ggt_top10:full_history:progress
    中断后再次触发自动跳过已完成的交易日，全部完成后清除进度记录。
    """
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量历史港股通十大成交股同步任务 concurrency={concurrency} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(GgtTop10Service.FULL_HISTORY_LOCK_KEY, timeout=14400, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量港股通十大成交股同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = GgtTop10Service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    update_state_fn=self.update_state,
                    concurrency=concurrency
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量历史港股通十大成交股同步结束: {result} ==========")
    return result
