"""
分红送股数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.dividend_service import DividendService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_dividend")
def sync_dividend_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    record_date: Optional[str] = None,
    ex_date: Optional[str] = None,
    imp_ann_date: Optional[str] = None
):
    """
    同步分红送股数据

    Args:
        ts_code: 股票代码
        ann_date: 公告日期 YYYYMMDD
        record_date: 股权登记日 YYYYMMDD
        ex_date: 除权除息日 YYYYMMDD
        imp_ann_date: 实施公告日 YYYYMMDD
        注意：至少需要一个参数

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行分红送股同步任务: ts_code={ts_code}, ann_date={ann_date}, record_date={record_date}, ex_date={ex_date}, imp_ann_date={imp_ann_date}")

        service = DividendService()
        result = run_async_in_celery(
            service.sync_dividend,
            ts_code=ts_code,
            ann_date=ann_date,
            record_date=record_date,
            ex_date=ex_date,
            imp_ann_date=imp_ann_date
        )

        if result["status"] == "success":
            logger.info(f"分红送股同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"分红送股同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行分红送股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
