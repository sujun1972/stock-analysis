"""
卖方盈利预测数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_report_rc")
def sync_report_rc_task(
    self,
    ts_code: Optional[str] = None,
    report_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sync_strategy: Optional[str] = None,
    max_requests_per_minute: Optional[int] = None,
):
    """增量同步卖方盈利预测数据"""
    try:
        logger.info(
            f"开始执行卖方盈利预测增量同步任务: strategy={sync_strategy} "
            f"ts_code={ts_code} report_date={report_date} "
            f"start_date={start_date} end_date={end_date}"
        )

        from app.services.report_rc_service import ReportRcService
        service = ReportRcService()

        if not any([ts_code, report_date, start_date, end_date]):
            result = run_async_in_celery(
                service.sync_incremental,
                sync_strategy=sync_strategy,
                max_requests_per_minute=max_requests_per_minute,
            )
        else:
            result = run_async_in_celery(
                service.sync_report_rc,
                ts_code=ts_code,
                report_date=report_date,
                start_date=start_date,
                end_date=end_date,
                sync_strategy=sync_strategy,
                max_requests_per_minute=max_requests_per_minute,
            )

        if result["status"] == "success":
            logger.info(f"卖方盈利预测数据同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"卖方盈利预测数据同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行卖方盈利预测数据同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_report_rc_full_history",
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,
)
def sync_report_rc_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    strategy: str = 'by_month',
    max_requests_per_minute: Optional[int] = None,
):
    """全量同步卖方盈利预测历史数据（按月切片，Redis Set 续继）"""
    from app.core.redis_lock import redis_client
    from app.core.redis_lock import redis_lock
    from app.tasks.sync_tasks import _DummyContext

    LOCK_KEY = 'sync:report_rc:full_history:lock'

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with (redis_lock.acquire(LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext()) as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        from app.services.report_rc_service import ReportRcService
        service = ReportRcService()
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
