"""
财务审计意见数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题

Author: Claude
Date: 2026-03-22
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.fina_audit_service import FinaAuditService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext

FINA_AUDIT_FULL_HISTORY_LOCK_KEY = "sync:fina_audit:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_fina_audit")
def sync_fina_audit_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    """
    同步财务审计意见数据

    Args:
        ts_code: 股票代码 TSXXXXXX.XX
        ann_date: 公告日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        period: 报告期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行财务审计意见同步任务: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

        service = FinaAuditService()
        result = run_async_in_celery(
            service.sync_fina_audit,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period
        )

        if result["status"] == "success":
            logger.info(f"财务审计意见同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"财务审计意见同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行财务审计意见同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_fina_audit_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400
)
def sync_fina_audit_full_history_task(self, start_date: str = None):
    """
    逐只股票全量同步财务审计意见历史数据（5 并发，Redis Set 续继）

    fina_audit 接口 ts_code 为必填，不支持全市场拉取，必须逐只请求。
    """
    from app.core.redis_lock import redis_client

    effective_start = start_date or '20090101'
    logger.info(f"========== [Celery] 开始全量财务审计意见同步任务，start_date={effective_start} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(FINA_AUDIT_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量财务审计意见同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = FinaAuditService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=effective_start,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(f"========== [Celery] 全量财务审计意见同步结束: {result} ==========")
    return result
