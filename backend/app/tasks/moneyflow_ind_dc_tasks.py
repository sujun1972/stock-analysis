"""
板块资金流向同步任务（东财概念及行业板块资金流向 DC）

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.extended_sync_service import ExtendedDataSyncService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_moneyflow_ind_dc")
def sync_moneyflow_ind_dc_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    content_type: Optional[str] = None
):
    """
    同步板块资金流向数据（东财概念及行业板块资金流向 DC）

    Args:
        ts_code: 代码
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        content_type: 资金类型(行业、概念、地域)

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行板块资金流向同步任务: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}, content_type={content_type}")

        service = ExtendedDataSyncService()
        result = run_async_in_celery(
            service.sync_moneyflow_ind_dc,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            content_type=content_type
        )

        if result["status"] == "success":
            logger.info(f"板块资金流向同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"板块资金流向同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行板块资金流向同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_ind_dc_daily")
def sync_moneyflow_ind_dc_daily_task(self):
    """
    每日定时同步板块资金流向数据

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日板块资金流向同步任务")

        # 不指定日期，让服务自动获取最新交易日
        return sync_moneyflow_ind_dc_task.apply_async(
            args=[],
            kwargs={
                'ts_code': None,
                'trade_date': None,
                'start_date': None,
                'end_date': None,
                'content_type': None
            }
        ).get()

    except Exception as e:
        logger.error(f"执行每日板块资金流向同步任务失败: {str(e)}")
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_ind_dc_range")
def sync_moneyflow_ind_dc_range_task(
    self,
    start_date: str,
    end_date: str,
    content_type: Optional[str] = None
):
    """
    同步指定日期范围的板块资金流向数据

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        content_type: 资金类型(行业、概念、地域)

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行板块资金流向范围同步任务: {start_date} - {end_date}, content_type={content_type}")

        return sync_moneyflow_ind_dc_task.apply_async(
            args=[],
            kwargs={
                'ts_code': None,
                'trade_date': None,
                'start_date': start_date,
                'end_date': end_date,
                'content_type': content_type
            }
        ).get()

    except Exception as e:
        logger.error(f"执行板块资金流向范围同步任务失败: {str(e)}")
        raise
