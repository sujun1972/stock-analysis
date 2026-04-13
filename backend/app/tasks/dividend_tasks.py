"""
分红送股数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.dividend_service import DividendService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext

DIVIDEND_FULL_HISTORY_LOCK_KEY = "sync:dividend:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_dividend")
def sync_dividend_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    record_date: Optional[str] = None,
    ex_date: Optional[str] = None,
    imp_ann_date: Optional[str] = None
):
    """
    同步分红送股数据

    Args:
        ts_code: 股票代码
        ann_date: 公告日期 YYYYMMDD
        record_date: 股权登记日 YYYYMMDD
        ex_date: 除权除息日 YYYYMMDD
        imp_ann_date: 实施公告日 YYYYMMDD
        注意：至少需要一个参数

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行分红送股同步任务: ts_code={ts_code}, ann_date={ann_date}, record_date={record_date}, ex_date={ex_date}, imp_ann_date={imp_ann_date}")

        service = DividendService()

        if not ts_code and not ann_date and not record_date and not ex_date and not imp_ann_date:
            result = run_async_in_celery(service.sync_incremental)
        else:
            result = run_async_in_celery(
                service.sync_dividend,
                ts_code=ts_code,
                ann_date=ann_date,
                record_date=record_date,
                ex_date=ex_date,
                imp_ann_date=imp_ann_date
            )

        if result.get("status") == "success":
            logger.info(f"分红送股同步成功: {result.get('records', 0)} 条")
            return result
        else:
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行分红送股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_dividend_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_dividend_full_history_task(self, start_date: str = None, concurrency: int = 5):
    """按季度报告期全量同步分红送股历史数据（支持中断续继）"""
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量分红送股同步任务，start_date={start_date}, concurrency={concurrency} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(DIVIDEND_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量分红送股同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = DividendService()
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

    logger.info(f"========== [Celery] 全量分红送股同步结束: {result} ==========")
    return result
