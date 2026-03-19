"""
融资融券交易汇总同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.margin_service import MarginService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_margin")
def sync_margin_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    exchange_id: Optional[str] = None
):
    """
    同步融资融券交易汇总数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行融资融券交易汇总同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange_id={exchange_id}")

        service = MarginService()
        result = run_async_in_celery(
            service.sync_margin,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            exchange_id=exchange_id
        )

        if result["status"] == "success":
            logger.info(f"融资融券交易汇总同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"融资融券交易汇总同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行融资融券交易汇总同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
