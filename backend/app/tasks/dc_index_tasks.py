"""
东方财富板块数据同步 Celery 任务
"""

import asyncio
from typing import Optional
from loguru import logger
from app.celery_app import celery_app
from app.services.dc_index_service import DcIndexService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_dc_index")
def sync_dc_index_task(
    self,
    ts_code: Optional[str] = None,
    name: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    idx_type: str = '概念板块'
):
    """
    同步东方财富板块数据

    Args:
        ts_code: 指数代码（可选）
        name: 板块名称（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        idx_type: 板块类型（默认：概念板块）
    """
    try:
        logger.info(f"开始执行东方财富板块数据同步任务: idx_type={idx_type}")
        service = DcIndexService()
        result = run_async_in_celery(
            service.sync_dc_index,
            ts_code=ts_code,
            name=name,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            idx_type=idx_type
        )
        if result["status"] == "success":
            logger.info(f"东方财富板块数据同步成功: {result['records']} 条")
            return result
        else:
            raise Exception(f"同步失败: {result.get('error', '未知错误')}")
    except Exception as e:
        logger.error(f"执行东方财富板块数据同步任务失败: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_dc_index_full_history",
    max_retries=0,
    soft_time_limit=14400,
    time_limit=18000,
    acks_late=False,
)
def sync_dc_index_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 3,
    idx_type: str = '概念板块',
    **kwargs
):
    """按自然月切片全量同步东方财富板块数据历史（支持中断续继）

    dc_index 每月数据量较大（每板块类型每天1000+条），并发默认3，避免超限。
    """
    from app.core.redis_lock import redis_client, redis_lock
    from app.tasks.sync_tasks import _DummyContext

    LOCK_KEY = f"sync:dc_index:full_history:lock:{idx_type}"
    logger.info(f"[Celery] 开始东方财富板块数据全量历史同步 idx_type={idx_type} start_date={start_date} concurrency={concurrency}")

    if redis_client is None:
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(LOCK_KEY, timeout=14400, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = DcIndexService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    concurrency=concurrency,
                    idx_type=idx_type,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(f"[Celery] 东方财富板块数据全量历史同步结束: 成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')}")
    return result
