"""
主营业务构成数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.fina_mainbz_service import FinaMainbzService
from app.tasks.extended_sync_tasks import run_async_in_celery

FINA_MAINBZ_FULL_HISTORY_LOCK_KEY = "sync:fina_mainbz:full_history:lock"


@celery_app.task(bind=True, name="tasks.sync_fina_mainbz")
def sync_fina_mainbz_task(
    self,
    ts_code: Optional[str] = None,
    period: Optional[str] = None,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步主营业务构成数据

    Args:
        ts_code: 股票代码 TSXXXXXX.XX
        period: 报告期 YYYYMMDD（每个季度最后一天的日期）
        type: 类型，P按产品 D按地区 I按行业
        start_date: 报告期开始日期 YYYYMMDD
        end_date: 报告期结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行主营业务构成同步任务: ts_code={ts_code}, period={period}, type={type}, start_date={start_date}, end_date={end_date}")

        service = FinaMainbzService()
        result = run_async_in_celery(
            service.sync_fina_mainbz,
            ts_code=ts_code,
            period=period,
            type=type,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"主营业务构成同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"主营业务构成同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行主营业务构成同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_fina_mainbz_full_history",
                 max_retries=0, soft_time_limit=28800, time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_fina_mainbz_full_history_task(self, start_date: Optional[str] = None, concurrency: int = 5):
    """
    全量历史同步主营业务构成数据（按季度 period 切片，支持 Redis 续继）

    Args:
        start_date: 起始日期 YYYYMMDD，默认 20090101
        concurrency: 并发数，默认 5

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始全量同步主营业务构成历史数据: start_date={start_date}, concurrency={concurrency}")

        try:
            from app.core.redis_lock import redis_lock, redis_client
        except ImportError:
            redis_lock = None
            redis_client = None

        class _DummyContext:
            def __enter__(self): return True
            def __exit__(self, *args): pass

        lock_ctx = redis_lock.acquire(FINA_MAINBZ_FULL_HISTORY_LOCK_KEY, timeout=28800, blocking=False) if redis_lock else _DummyContext()

        with lock_ctx as acquired:
            if not acquired and redis_lock:
                logger.warning("全量同步主营业务构成任务已在运行，跳过")
                return {"status": "skipped", "message": "任务已在运行"}

            service = FinaMainbzService()
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

        logger.info(f"全量同步主营业务构成完成: {result}")
        return result

    except Exception as e:
        logger.error(f"全量同步主营业务构成失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
