"""
东方财富概念板块行情同步 Celery 任务
"""

from typing import Optional
from loguru import logger
from app.celery_app import celery_app
from app.services.dc_daily_service import DcDailyService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_dc_daily")
def sync_dc_daily_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    idx_type: Optional[str] = None
):
    """
    同步东方财富概念板块行情数据

    Args:
        ts_code: 板块代码（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        idx_type: 板块类型（可选）
    """
    try:
        logger.info(f"开始执行东方财富概念板块行情同步任务: trade_date={trade_date}")
        service = DcDailyService()
        result = run_async_in_celery(
            service.sync_dc_daily,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            idx_type=idx_type
        )
        if result["status"] == "success":
            logger.info(f"东方财富概念板块行情同步成功: {result['records']} 条")
            return result
        else:
            raise Exception(f"同步失败: {result.get('error', '未知错误')}")
    except Exception as e:
        logger.error(f"执行东方财富概念板块行情同步任务失败: {str(e)}")
        raise
