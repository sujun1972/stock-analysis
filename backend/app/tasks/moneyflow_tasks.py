"""
个股资金流向同步任务（Tushare标准接口）

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
数据源：Tushare pro.moneyflow() - 基于主动买卖单统计的资金流向
积分消耗：2000积分/次（单次最大6000行）
"""

from typing import Optional, List
import asyncio
from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_moneyflow")
def sync_moneyflow_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    **kwargs  # 接受额外参数（如 strategy, priority 等）用于向后兼容
):
    """
    同步个股资金流向数据（Tushare标准接口）

    Args:
        ts_code: 股票代码（单个）
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        stock_list: 股票代码列表（批量）
        **kwargs: 额外参数（strategy, priority, points_consumption 等）

    Returns:
        同步结果

    注意：
        - 股票和时间参数至少输入一个
        - 单次最大提取6000行记录
        - 需要2000积分权限
    """
    try:
        logger.info(f"开始执行个股资金流向同步任务: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService
        service = MoneyflowSyncService()
        result = run_async_in_celery(
            service.sync_moneyflow,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list
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


@celery_app.task(bind=True, name="tasks.sync_moneyflow_daily")
def sync_moneyflow_daily_task(self, **kwargs):
    """
    每日定时同步个股资金流向数据（活跃股票）

    默认获取最新交易日的活跃股票资金流向数据

    Args:
        **kwargs: 额外参数（用于向后兼容）

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日个股资金流向同步任务")

        # 不指定参数，让服务自动获取最新交易日的活跃股票数据
        return sync_moneyflow_task.apply_async(
            args=[],
            kwargs={
                'ts_code': None,
                'trade_date': None,
                'start_date': None,
                'end_date': None,
                'stock_list': None
            }
        ).get()

    except Exception as e:
        logger.error(f"执行每日个股资金流向同步任务失败: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    name="tasks.sync_moneyflow_full_history",
    max_retries=0,
    soft_time_limit=28800,
    time_limit=32400,
    acks_late=False,  # 支持续继，worker 重启后不自动重新入队
)
def sync_moneyflow_full_history_task(
    self,
    start_date: Optional[str] = None,
    concurrency: int = 5,
    **kwargs
):
    """
    按股票代码逐只同步个股资金流向全量历史数据

    支持中断续继：任务中断后再次触发，自动跳过已完成的股票。
    进度存储：Redis Set key = sync:moneyflow:full_history:progress

    Args:
        start_date: 开始日期 YYYYMMDD，默认 20100101
        concurrency: 并发数，来自 sync_configs.full_sync_concurrency，默认 5
    """
    from app.core.redis_lock import redis_client
    from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService

    logger.info(f"========== [Celery] 开始个股资金流向全量历史同步任务 start_date={start_date} concurrency={concurrency} ==========")

    if redis_client is None:
        logger.error("Redis 不可用，无法执行全量同步任务")
        return {"status": "error", "message": "Redis 不可用"}

    service = MoneyflowSyncService()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            service.sync_moneyflow_full_history(
                redis_client=redis_client,
                start_date=start_date,
                concurrency=concurrency,
                update_state_fn=self.update_state
            )
        )
    finally:
        loop.close()

    logger.info(
        f"========== [Celery] 个股资金流向全量历史同步结束: "
        f"成功={result.get('success')}, 跳过={result.get('skipped')}, 失败={result.get('errors')} =========="
    )
    return result


@celery_app.task(bind=True, name="tasks.sync_moneyflow_range")
def sync_moneyflow_range_task(
    self,
    start_date: str,
    end_date: str,
    ts_code: Optional[str] = None,
    stock_list: Optional[List[str]] = None,
    **kwargs
):
    """
    同步指定日期范围的个股资金流向数据

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        ts_code: 股票代码（单个，可选）
        stock_list: 股票代码列表（批量，可选）
        **kwargs: 额外参数（用于向后兼容）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行个股资金流向范围同步任务: {start_date} - {end_date}, ts_code={ts_code}")

        return sync_moneyflow_task.apply_async(
            args=[],
            kwargs={
                'ts_code': ts_code,
                'trade_date': None,
                'start_date': start_date,
                'end_date': end_date,
                'stock_list': stock_list
            }
        ).get()

    except Exception as e:
        logger.error(f"执行个股资金流向范围同步任务失败: {str(e)}")
        raise
