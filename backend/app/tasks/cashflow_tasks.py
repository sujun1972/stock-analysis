"""
现金流量表同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.cashflow_service import CashflowService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_cashflow")
def sync_cashflow_task(
    self,
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: Optional[str] = None,
    report_type: Optional[str] = None
):
    """
    同步现金流量表数据

    Args:
        ts_code: 股票代码 (可选)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        period: 报告期 YYYYMMDD
        report_type: 报告类型 (1-12)

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行现金流量表同步任务: ts_code={ts_code}, period={period}, start_date={start_date}, end_date={end_date}, report_type={report_type}")

        service = CashflowService()
        result = run_async_in_celery(
            service.sync_cashflow,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type
        )

        if result["status"] == "success":
            logger.info(f"现金流量表同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"现金流量表同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行现金流量表同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
