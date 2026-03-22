"""
财务审计意见数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题

Author: Claude
Date: 2026-03-22
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.fina_audit_service import FinaAuditService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_fina_audit")
def sync_fina_audit_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None
):
    """
    同步财务审计意见数据

    Args:
        ts_code: 股票代码 TSXXXXXX.XX
        ann_date: 公告日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        period: 报告期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行财务审计意见同步任务: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

        service = FinaAuditService()
        result = run_async_in_celery(
            service.sync_fina_audit,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period
        )

        if result["status"] == "success":
            logger.info(f"财务审计意见同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"财务审计意见同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行财务审计意见同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
