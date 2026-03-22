"""
资产负债表同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.balancesheet_service import BalancesheetService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_balancesheet")
def sync_balancesheet_task(
    self,
    ts_code: Optional[str] = None,
    period: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    report_type: str = '1',
    comp_type: Optional[str] = None
):
    """
    同步资产负债表数据

    Args:
        ts_code: 股票代码 XXXXXX.XX
        period: 报告期 YYYYMMDD (如 20231231表示年报)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        report_type: 报告类型（默认1-合并报表）
        comp_type: 公司类型（1一般工商业2银行3保险4证券）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行资产负债表同步任务: ts_code={ts_code}, period={period}, "
                   f"start_date={start_date}, end_date={end_date}")

        service = BalancesheetService()
        result = run_async_in_celery(
            service.sync_balancesheet,
            ts_code=ts_code,
            period=period,
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
            comp_type=comp_type
        )

        if result["status"] == "success":
            logger.info(f"资产负债表同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"资产负债表同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行资产负债表同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
