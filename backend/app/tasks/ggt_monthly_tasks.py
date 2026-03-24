"""
港股通每月成交统计数据同步任务
"""

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.ggt_monthly_service import GgtMonthlyService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_ggt_monthly")
def sync_ggt_monthly_task(
    self,
    month: str = None,
    start_month: str = None,
    end_month: str = None
):
    """
    同步港股通每月成交统计数据

    Args:
        month: 月度 YYYYMM,支持多个输入(可选)
        start_month: 开始月度 YYYYMM(可选)
        end_month: 结束月度 YYYYMM(可选)

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行港股通每月成交统计同步任务")
        logger.info(f"参数: month={month}, start_month={start_month}, end_month={end_month}")

        # 使用辅助函数运行异步代码
        service = GgtMonthlyService()
        result = run_async_in_celery(
            service.sync_data,
            month=month,
            start_month=start_month,
            end_month=end_month
        )

        logger.info(f"港股通每月成交统计同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"港股通每月成交统计同步任务失败: {e}")
        raise
