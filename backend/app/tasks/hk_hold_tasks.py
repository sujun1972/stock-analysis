"""
沪深港股通持股明细数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.hk_hold_service import HkHoldService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_hk_hold")
def sync_hk_hold_task(
    self,
    code: Optional[str] = None,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    exchange: Optional[str] = None
):
    """
    同步沪深港股通持股明细数据

    Args:
        code: 原始代码（如 90000）
        ts_code: 股票代码（如 600000.SH）
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        exchange: 类型：SH沪股通 SZ深股通 HK港股通

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行沪深港股通持股明细数据同步任务: code={code}, ts_code={ts_code}, "
                   f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange={exchange}")

        service = HkHoldService()
        result = run_async_in_celery(
            service.sync_hk_hold,
            code=code,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange
        )

        if result["status"] == "success":
            logger.info(f"沪深港股通持股明细数据同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"沪深港股通持股明细数据同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行沪深港股通持股明细数据同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
