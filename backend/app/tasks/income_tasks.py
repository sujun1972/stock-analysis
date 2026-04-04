"""
利润表数据同步Celery任务
"""

import asyncio
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.income_service import IncomeService
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext
from loguru import logger

INCOME_FULL_HISTORY_LOCK_KEY = "sync:income:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_income")
def sync_income_task(
    self,
    ts_code: str = None,
    period: str = None,
    start_date: str = None,
    end_date: str = None,
    report_type: str = None
):
    """
    同步利润表数据任务

    Args:
        ts_code: 股票代码
        period: 报告期（YYYYMMDD或YYYYQQ格式）
        start_date: 开始日期
        end_date: 结束日期
        report_type: 报告类型（1-12）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行利润表同步任务: ts_code={ts_code}, period={period}, "
                   f"start_date={start_date}, end_date={end_date}, report_type={report_type}")

        # 使用辅助函数运行异步代码
        service = IncomeService()
        result = run_async_in_celery(
            service.sync_income,
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )

        logger.info(f"利润表同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"利润表同步任务失败: {e}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_income_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400
)
def sync_income_full_history_task(self, start_date: str = None):
    """
    按季度报告期全量同步利润表历史数据（支持中断续继）

    逐季调用 income_vip(period=YYYYMMDD)，3 并发，Redis Set 记录已完成 period，
    中断后再次触发自动跳过已完成季度，直到全部完成后清除进度记录。

    Args:
        start_date: 起始日期 YYYYMMDD，不传则使用 '20090101'
    """
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量利润表数据同步任务，start_date={start_date} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(INCOME_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量利润表同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = IncomeService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量利润表同步结束: {result} ==========")
    return result
