"""
个股资金流向同步任务（东方财富DC）

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

import asyncio
from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_moneyflow_stock_dc")
def sync_moneyflow_stock_dc_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步个股资金流向数据（东方财富DC）

    Args:
        ts_code: 股票代码
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行个股资金流向同步任务: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        # 每次在任务内部创建新实例，避免复用 fork 前建立的全局单例中已损坏的连接池
        from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService
        service = MoneyflowSyncService()

        if not any([ts_code, trade_date, start_date, end_date]):
            result = run_async_in_celery(service.sync_moneyflow_stock_dc_incremental)
        else:
            result = run_async_in_celery(
                service.sync_moneyflow_stock_dc,
                ts_code=ts_code,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

        if result["status"] == "success":
            logger.info(f"个股资金流向同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"个股资金流向同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行个股资金流向同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_stock_dc_daily")
def sync_moneyflow_stock_dc_daily_task(self):
    """
    每日定时同步个股资金流向数据（获取当日全部股票）

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日个股资金流向同步任务")

        # 不指定股票代码和日期，让服务自动获取最新交易日的全部股票数据
        return sync_moneyflow_stock_dc_task.apply_async(
            args=[],
            kwargs={'ts_code': None, 'trade_date': None, 'start_date': None, 'end_date': None}
        ).get()

    except Exception as e:
        logger.error(f"执行每日个股资金流向同步任务失败: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_moneyflow_stock_dc_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_moneyflow_stock_dc_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    **kwargs
):
    """
    按股票代码逐只同步个股资金流向（DC）全量历史数据

    支持中断续继：任务中断后再次触发，自动跳过已完成的股票。
    进度存储：Redis Set key = sync:moneyflow_stock_dc:full_history:progress
    数据起始：20230911（DC 接口最早数据日期）

    Args:
        start_date: 开始日期 YYYYMMDD，默认 20230911
        concurrency: 并发数，来自 sync_configs.full_sync_concurrency，默认 5
    """
    from app.core.redis_lock import redis_client
    from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService

    logger.info(
        f"========== [Celery] 开始个股资金流向（DC）全量历史同步任务 "
        f"start_date={start_date} concurrency={concurrency} =========="
    )

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    service = MoneyflowSyncService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            service.sync_moneyflow_stock_dc_full_history(
                redis_client=redis_client,
                start_date=start_date,
                concurrency=concurrency,
                update_state_fn=self.update_state
            )
        )
    finally:
        loop.close()

    logger.info(
        f"========== [Celery] 个股资金流向（DC）全量历史同步结束: "
        f"成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')} =========="
    )
    return result


@celery_app.task(bind=True, name="tasks.sync_moneyflow_stock_dc_range")
def sync_moneyflow_stock_dc_range_task(
    self,
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None
):
    """
    同步指定日期范围的个股资金流向数据

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        ts_code: 股票代码（可选，不指定则获取全部股票）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行个股资金流向范围同步任务: {start_date} - {end_date}, ts_code={ts_code}")

        return sync_moneyflow_stock_dc_task.apply_async(
            args=[],
            kwargs={'ts_code': ts_code, 'trade_date': None, 'start_date': start_date, 'end_date': end_date}
        ).get()

    except Exception as e:
        logger.error(f"执行个股资金流向范围同步任务失败: {str(e)}")
        raise
