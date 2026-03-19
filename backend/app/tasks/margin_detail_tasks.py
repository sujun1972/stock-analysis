"""
融资融券交易明细同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.margin_detail_service import MarginDetailService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_margin_detail")
def sync_margin_detail_task(
    self,
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步融资融券交易明细数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        ts_code: TS股票代码
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行融资融券交易明细同步任务: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

        service = MarginDetailService()
        result = run_async_in_celery(
            service.sync_margin_detail,
            trade_date=trade_date,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"融资融券交易明细同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"融资融券交易明细同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行融资融券交易明细同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
