"""
现金流量表同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.cashflow_service import CashflowService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext

CASHFLOW_FULL_HISTORY_LOCK_KEY = "sync:cashflow:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_cashflow")
def sync_cashflow_task(
    self,
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None,
    report_type: Optional[str] = None
):
    """
    同步现金流量表数据

    Args:
        ts_code: 股票代码 (可选)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        period: 报告期 YYYYMMDD
        report_type: 报告类型 (1-12)

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行现金流量表同步任务: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}, report_type={report_type}")

        service = CashflowService()
        result = run_async_in_celery(
            service.sync_cashflow,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type
        )

        if result["status"] == "success":
            logger.info(f"现金流量表同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"现金流量表同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行现金流量表同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_cashflow_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_cashflow_full_history_task(self, start_date: str = None, concurrency: int = 5):
    """
    逐只股票全量同步现金流量表历史数据（5 并发，Redis Set 续继）

    按 ts_code 逐只调用 cashflow_vip，每只股票数据量极少，彻底避免 Tushare
    单次返回上限导致的数据截断。Redis Set 记录已完成 ts_code，中断后自动续继。

    Args:
        start_date: 起始日期 YYYYMMDD，不传则使用 '20090101'
        concurrency: 并发数，默认 5
    """
    from app.core.redis_lock import redis_client

    logger.info(f"========== [Celery] 开始全量现金流量表同步任务，start_date={start_date}, concurrency={concurrency} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(CASHFLOW_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量现金流量表同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = CashflowService()
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

    logger.info(f"========== [Celery] 全量现金流量表同步结束: {result} ==========")
    return result
