"""
大盘资金流向同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.extended_sync_service import ExtendedDataSyncService
from app.tasks.extended_sync_tasks import run_async_in_celery


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

        service = ExtendedDataSyncService()
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
