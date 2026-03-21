"""
连板天梯同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.limit_step_service import LimitStepService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_limit_step")
def sync_limit_step_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ts_code: Optional[str] = None,
    nums: Optional[str] = None
):
    """
    同步连板天梯数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        ts_code: 股票代码（可选）
        nums: 连板次数（可选，支持多个，如 "2,3"）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行连板天梯同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, nums={nums}")

        service = LimitStepService()
        result = run_async_in_celery(
            service.sync_limit_step,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            nums=nums
        )

        if result["status"] == "success":
            logger.info(f"连板天梯同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"连板天梯同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行连板天梯同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
