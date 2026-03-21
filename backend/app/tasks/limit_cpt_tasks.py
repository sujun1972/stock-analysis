"""
最强板块统计 Celery 任务
"""
from typing import Optional
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.limit_cpt_service import LimitCptService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_limit_cpt")
def sync_limit_cpt_task(
    self,
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步最强板块统计数据

    Args:
        trade_date: 交易日期，格式：YYYYMMDD（可选，默认为当天）
        ts_code: 板块代码（可选）
        start_date: 开始日期，格式：YYYYMMDD（可选）
        end_date: 结束日期，格式：YYYYMMDD（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行最强板块统计同步任务: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

        # 使用辅助函数运行异步代码
        service = LimitCptService()
        result = run_async_in_celery(
            service.sync_limit_cpt,
            trade_date=trade_date,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"最强板块统计同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"最强板块统计同步任务失败: {e}")
        raise
