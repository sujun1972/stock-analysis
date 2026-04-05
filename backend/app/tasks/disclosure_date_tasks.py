"""
财报披露计划同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.disclosure_date_service import DisclosureDateService
from app.tasks.extended_sync_tasks import run_async_in_celery

DISCLOSURE_DATE_FULL_HISTORY_LOCK_KEY = "sync:disclosure_date:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_disclosure_date")
def sync_disclosure_date_task(
    self,
    ts_code: Optional[str] = None,
    end_date: Optional[str] = None,
    pre_date: Optional[str] = None,
    ann_date: Optional[str] = None,
    actual_date: Optional[str] = None
):
    """
    同步财报披露计划数据

    Args:
        ts_code: 股票代码 (TS格式)
        end_date: 报告期 YYYYMMDD（每个季度最后一天）
        pre_date: 计划披露日期 YYYYMMDD
        ann_date: 最新披露公告日 YYYYMMDD
        actual_date: 实际披露日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行财报披露计划同步任务: ts_code={ts_code}, end_date={end_date}, "
                   f"pre_date={pre_date}, ann_date={ann_date}, actual_date={actual_date}")

        service = DisclosureDateService()
        result = run_async_in_celery(
            service.sync_disclosure_date,
            ts_code=ts_code,
            end_date=end_date,
            pre_date=pre_date,
            ann_date=ann_date,
            actual_date=actual_date
        )

        if result["status"] == "success":
            logger.info(f"财报披露计划同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"财报披露计划同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行财报披露计划同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_disclosure_date_full_history",
                 max_retries=0, soft_time_limit=28800, time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_disclosure_date_full_history_task(self, start_date: Optional[str] = None):
    """
    全量历史同步财报披露计划数据（按季度 period 切片，支持 Redis 续继）

    Args:
        start_date: 起始日期 YYYYMMDD，默认 20090101

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始全量同步财报披露计划历史数据: start_date={start_date}")

        try:
            from app.core.redis_lock import redis_lock, redis_client
        except ImportError:
            redis_lock = None
            redis_client = None

        class _DummyContext:
            def __enter__(self): return True
            def __exit__(self, *args): pass

        lock_ctx = redis_lock.acquire(DISCLOSURE_DATE_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext()

        with lock_ctx as acquired:
            if not acquired and redis_lock:
                logger.warning("全量同步财报披露计划任务已在运行，跳过")
                return {"status": "skipped", "message": "任务已在运行"}

            service = DisclosureDateService()
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

        logger.info(f"全量同步财报披露计划完成: {result}")
        return result

    except Exception as e:
        logger.error(f"全量同步财报披露计划失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
