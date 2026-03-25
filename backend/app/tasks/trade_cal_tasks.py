"""
交易日历 Celery 任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题。
"""
import traceback
from typing import Optional

from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.trading_calendar_service import TradingCalendarService


@celery_app.task(bind=True, name="tasks.sync_trade_cal")
def sync_trade_cal_task(
    self,
    exchange: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步交易日历数据

    Args:
        exchange: 交易所代码（可选，默认同步 SSE 和 SZSE）
        start_date: 开始日期，格式：YYYYMMDD（可选）
        end_date: 结束日期，格式：YYYYMMDD（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行交易日历同步任务: exchange={exchange}, start_date={start_date}, end_date={end_date}")

        service = TradingCalendarService()
        result = run_async_in_celery(
            service.sync_trade_calendar,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"交易日历同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"交易日历同步失败: {result}")
            error_msg = result.get('message', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行交易日历同步任务失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise
