"""
个股异常波动同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.stk_shock_service import StkShockService
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_stk_shock")
def sync_stk_shock_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ts_code: Optional[str] = None
):
    """
    同步个股异常波动数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        ts_code: 股票代码（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行个股异常波动同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, ts_code={ts_code}")

        service = StkShockService()
        result = run_async_in_celery(
            service.sync_stk_shock,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )

        if result["status"] == "success":
            logger.info(f"个股异常波动同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"个股异常波动同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行个股异常波动同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_stk_shock_full_history",
    max_retries=0,
    soft_time_limit=300,
    time_limit=600
)
def sync_stk_shock_full_history_task(self, start_date: str = None):
    """全量同步个股异常波动数据（单次请求）

    stk_shock 接口为快照接口，不支持日期范围过滤，单次拉取全量当前数据。
    start_date 参数保留以与其他全量同步任务保持接口一致，不会传给接口。
    """
    from app.core.redis_lock import redis_client

    logger.info("========== [Celery] 开始全量历史个股异常波动同步任务 ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(StkShockService.FULL_HISTORY_LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量个股异常波动同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = StkShockService()
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

    logger.info(f"========== [Celery] 全量历史个股异常波动同步结束: {result} ==========")
    return result
