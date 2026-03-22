"""
业绩预告同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.forecast_service import ForecastService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_forecast")
def sync_forecast_task(
    self,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None,
    type_: Optional[str] = None
):
    """
    同步业绩预告数据

    Args:
        ann_date: 公告日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        period: 报告期 YYYYMMDD
        type_: 预告类型

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行业绩预告同步任务: ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}, type={type_}")

        service = ForecastService()
        result = run_async_in_celery(
            service.sync_forecast,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            type_=type_
        )

        if result["status"] == "success":
            logger.info(f"业绩预告同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"业绩预告同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行业绩预告同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
