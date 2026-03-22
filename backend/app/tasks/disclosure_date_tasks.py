"""
财报披露计划同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.disclosure_date_service import DisclosureDateService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_disclosure_date")
def sync_disclosure_date_task(
    self,
    ts_code: Optional[str] = None,
    end_date: Optional[str] = None,
    pre_date: Optional[str] = None,
    ann_date: Optional[str] = None,
    actual_date: Optional[str] = None
):
    """
    同步财报披露计划数据

    Args:
        ts_code: 股票代码 (TS格式)
        end_date: 报告期 YYYYMMDD（每个季度最后一天）
        pre_date: 计划披露日期 YYYYMMDD
        ann_date: 最新披露公告日 YYYYMMDD
        actual_date: 实际披露日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行财报披露计划同步任务: ts_code={ts_code}, end_date={end_date}, "
                   f"pre_date={pre_date}, ann_date={ann_date}, actual_date={actual_date}")

        service = DisclosureDateService()
        result = run_async_in_celery(
            service.sync_disclosure_date,
            ts_code=ts_code,
            end_date=end_date,
            pre_date=pre_date,
            ann_date=ann_date,
            actual_date=actual_date
        )

        if result["status"] == "success":
            logger.info(f"财报披露计划同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"财报披露计划同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行财报披露计划同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
