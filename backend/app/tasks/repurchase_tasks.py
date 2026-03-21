"""
股票回购同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.repurchase_service import RepurchaseService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_repurchase")
def sync_repurchase_task(
    self,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步股票回购数据

    Args:
        ann_date: 公告日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行股票回购同步任务: ann_date={ann_date}, start_date={start_date}, end_date={end_date}")

        service = RepurchaseService()
        result = run_async_in_celery(
            service.sync_repurchase,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"股票回购同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"股票回购同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行股票回购同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
