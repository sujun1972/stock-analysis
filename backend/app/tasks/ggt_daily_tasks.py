"""
港股通每日成交统计数据同步任务
"""

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.ggt_daily_service import GgtDailyService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_ggt_daily")
def sync_ggt_daily_task(
    self,
    trade_date: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    同步港股通每日成交统计数据

    Args:
        trade_date: 交易日期 YYYYMMDD，支持单日和多日输入（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行港股通每日成交统计同步任务")
        logger.info(f"参数: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        # 使用辅助函数运行异步代码
        service = GgtDailyService()
        result = run_async_in_celery(
            service.sync_data,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"港股通每日成交统计同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"港股通每日成交统计同步任务失败: {e}")
        raise
