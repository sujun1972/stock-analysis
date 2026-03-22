"""
业绩快报数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.express_service import ExpressService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_express")
def sync_express_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    """
    同步业绩快报数据

    Args:
        ts_code: 股票代码（可选）
        ann_date: 公告日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        period: 报告期 YYYYMMDD（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行业绩快报同步任务: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

        service = ExpressService()
        result = run_async_in_celery(
            service.sync_express,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period
        )

        if result["status"] == "success":
            logger.info(f"业绩快报同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"业绩快报同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行业绩快报同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
