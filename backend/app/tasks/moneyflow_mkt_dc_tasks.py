"""
大盘资金流向同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.tasks.sync_tasks import _DummyContext


@celery_app.task(bind=True, name="tasks.sync_moneyflow_mkt_dc")
def sync_moneyflow_mkt_dc_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步大盘资金流向数据（东方财富DC）

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行大盘资金流向同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        # 延迟导入，避免模块级单例在 fork 前被初始化导致连接池损坏
        from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService
        service = MoneyflowSyncService()
        result = run_async_in_celery(
            service.sync_moneyflow_mkt_dc,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"大盘资金流向同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"大盘资金流向同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行大盘资金流向同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_mkt_dc_daily")
def sync_moneyflow_mkt_dc_daily_task(self):
    """
    每日定时同步大盘资金流向数据

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日大盘资金流向同步任务")

        # 不指定日期，让服务自动获取最新交易日
        return sync_moneyflow_mkt_dc_task.apply_async(
            args=[],
            kwargs={'trade_date': None, 'start_date': None, 'end_date': None}
        ).get()

    except Exception as e:
        logger.error(f"执行每日大盘资金流向同步任务失败: {str(e)}")
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_mkt_dc_range")
def sync_moneyflow_mkt_dc_range_task(
    self,
    start_date: str,
    end_date: str
):
    """
    同步指定日期范围的大盘资金流向数据

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行大盘资金流向范围同步任务: {start_date} - {end_date}")

        return sync_moneyflow_mkt_dc_task.apply_async(
            args=[],
            kwargs={'trade_date': None, 'start_date': start_date, 'end_date': end_date}
        ).get()

    except Exception as e:
        logger.error(f"执行大盘资金流向范围同步任务失败: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_moneyflow_mkt_dc_full_history",
    max_retries=0,
    soft_time_limit=7200,
    time_limit=10800,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_moneyflow_mkt_dc_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    **kwargs
):
    """
    按自然月切片全量同步大盘资金流向历史数据（支持中断续继）

    大盘DC每天一条记录，每月约 20 条，按月切片远低于 5000 上限。
    Redis Set 记录已完成月份（key = 月起始日期），支持中断后续继。

    Args:
        start_date: 开始日期 YYYYMMDD，默认 20150101
        concurrency: 并发数，来自 sync_configs.full_sync_concurrency，默认 5
    """
    from app.core.redis_lock import redis_client, redis_lock
    from app.services.moneyflow_mkt_dc_service import MoneyflowMktDcService

    LOCK_KEY = "sync:moneyflow_mkt_dc:full_history:lock"

    logger.info(
        f"========== [Celery] 开始大盘资金流向（DC）全量历史同步任务 "
        f"start_date={start_date} concurrency={concurrency} =========="
    )

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    with redis_lock.acquire(LOCK_KEY, timeout=7200, blocking=False) if redis_lock else _DummyContext() as acquired:
        if not acquired and redis_lock:
            logger.warning("⚠️  全量大盘资金流向同步任务已在执行中，跳过本次执行")
            return {"status": "locked", "message": "已有全量同步任务正在进行"}

        service = MoneyflowMktDcService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                service.sync_full_history(
                    redis_client=redis_client,
                    start_date=start_date,
                    concurrency=concurrency,
                    update_state_fn=self.update_state
                )
            )
        finally:
            loop.close()

    logger.info(
        f"========== [Celery] 大盘资金流向（DC）全量历史同步结束: "
        f"成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')} =========="
    )
    return result
