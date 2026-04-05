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
    ts_code: Optional[str] = None
):
    """
    同步股权质押统计数据

    Args:
        trade_date: 交易日期 YYYYMMDD (实际为end_date)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        ts_code: 股票代码

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行股权质押统计同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, ts_code={ts_code}")

        service = PledgeStatService()
        result = run_async_in_celery(
            service.sync_pledge_stat,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
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
def sync_pledge_stat_full_history_task(self, start_date: str = None, concurrency: int = 5):
    """逐只股票全量同步股权质押统计历史数据（支持中断续继）

    pledge_stat 接口只支持 ts_code + end_date，无法按日期范围拉全市场，
    因此采用逐只股票请求方式，5并发，每批50只，约5500只。
    """
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
                    update_state_fn=self.update_state,
                    concurrency=concurrency
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量历史股权质押统计同步结束: {result} ==========")
    return result
