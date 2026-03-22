"""
限售股解禁同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.share_float_service import ShareFloatService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_share_float")
def sync_share_float_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    float_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步限售股解禁数据

    Args:
        ts_code: 股票代码
        ann_date: 公告日期 YYYYMMDD
        float_date: 解禁日期 YYYYMMDD
        start_date: 解禁开始日期 YYYYMMDD
        end_date: 解禁结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行限售股解禁同步任务: ts_code={ts_code}, ann_date={ann_date}, "
                   f"float_date={float_date}, start_date={start_date}, end_date={end_date}")

        service = ShareFloatService()
        result = run_async_in_celery(
            service.sync_share_float,
            ts_code=ts_code,
            ann_date=ann_date,
            float_date=float_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"限售股解禁同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"限售股解禁同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行限售股解禁同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
