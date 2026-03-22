"""
利润表数据同步Celery任务
"""

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.income_service import IncomeService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_income")
def sync_income_task(
    self,
    ts_code: str = None,
    period: str = None,
    start_date: str = None,
    end_date: str = None,
    report_type: str = None
):
    """
    同步利润表数据任务

    Args:
        ts_code: 股票代码
        period: 报告期（YYYYMMDD或YYYYQQ格式）
        start_date: 开始日期
        end_date: 结束日期
        report_type: 报告类型（1-12）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行利润表同步任务: ts_code={ts_code}, period={period}, "
                   f"start_date={start_date}, end_date={end_date}, report_type={report_type}")

        # 使用辅助函数运行异步代码
        service = IncomeService()
        result = run_async_in_celery(
            service.sync_income,
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )

        logger.info(f"利润表同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"利润表同步任务失败: {e}")
        raise
