"""
券商每月荐股同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.broker_recommend_service import BrokerRecommendService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_broker_recommend")
def sync_broker_recommend_task(
    self,
    month: Optional[str] = None
):
    """
    同步券商每月荐股数据

    Args:
        month: 月度 YYYYMM（可选,不传则同步当前月）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行券商荐股同步任务: month={month}")

        service = BrokerRecommendService()
        result = run_async_in_celery(
            service.sync_broker_recommend,
            month=month
        )

        if result["status"] == "success":
            logger.info(f"券商荐股同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"券商荐股同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行券商荐股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
