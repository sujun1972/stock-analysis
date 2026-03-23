"""
股票收盘集合竞价同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.stk_auction_c_service import StkAuctionCService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_stk_auction_c")
def sync_stk_auction_c_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步股票收盘集合竞价数据

    Args:
        ts_code: 股票代码
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行收盘集合竞价同步任务: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        service = StkAuctionCService()
        result = run_async_in_celery(
            service.sync_stk_auction_c,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"收盘集合竞价同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"收盘集合竞价同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行收盘集合竞价同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
