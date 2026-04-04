"""
沪深股通十大成交股同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.hsgt_top10_service import HsgtTop10Service
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.core.redis_lock import redis_lock
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_hsgt_top10")
def sync_hsgt_top10_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    market_type: Optional[str] = None
):
    """
    同步沪深股通十大成交股数据

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        market_type: 市场类型 1:沪市 3:深市（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行沪深股通十大成交股同步任务: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

        service = HsgtTop10Service()
        result = run_async_in_celery(
            service.sync_hsgt_top10,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )

        if result["status"] == "success":
            logger.info(f"沪深股通十大成交股同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"沪深股通十大成交股同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行沪深股通十大成交股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_hsgt_top10_full_history",
    max_retries=0,
    soft_time_limit=14400,
    time_limit=18000
)
def sync_hsgt_top10_full_history_task(self, start_date: Optional[str] = None):
    """
    按月切片全量同步沪深股通十大成交股历史数据（支持中断续继）

    每月约 440 条（20条/天×22天），安全低于 Tushare 5000 条单次上限。
    5 并发，约 120 个月段（2015年起）。

    Args:
        start_date: 同步起始日期 YYYYMMDD，不传则从 2015-01-01 开始

    进度存储：Redis Set key = sync:hsgt_top10:full_history:progress
    中断后再次触发自动跳过已完成的月段，全部完成后清除进度记录。
    """
    from app.core.redis_lock import redis_client

    logger.info("========== [Celery] 开始全量历史沪深股通十大成交股同步任务 ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(HsgtTop10Service.FULL_HISTORY_LOCK_KEY, timeout=14400, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量沪深股通十大成交股同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = HsgtTop10Service()
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

    logger.info(f"========== [Celery] 全量历史沪深股通十大成交股同步结束: {result} ==========")
    return result
