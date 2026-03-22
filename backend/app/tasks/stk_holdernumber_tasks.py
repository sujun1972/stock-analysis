"""
股东人数同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.stk_holdernumber_service import StkHolderNumberService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_stk_holdernumber")
def sync_stk_holdernumber_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步股东人数数据

    Args:
        ts_code: 股票代码（可选）
        ann_date: 公告日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(
            f"开始执行股东人数同步任务: ts_code={ts_code}, ann_date={ann_date}, "
            f"start_date={start_date}, end_date={end_date}"
        )

        service = StkHolderNumberService()
        result = run_async_in_celery(
            service.sync_stk_holdernumber,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"股东人数同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"股东人数同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行股东人数同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
