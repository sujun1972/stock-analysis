"""
主营业务构成数据同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.fina_mainbz_service import FinaMainbzService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_fina_mainbz")
def sync_fina_mainbz_task(
    self,
    ts_code: Optional[str] = None,
    period: Optional[str] = None,
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步主营业务构成数据

    Args:
        ts_code: 股票代码 TSXXXXXX.XX
        period: 报告期 YYYYMMDD（每个季度最后一天的日期）
        type: 类型，P按产品 D按地区 I按行业
        start_date: 报告期开始日期 YYYYMMDD
        end_date: 报告期结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行主营业务构成同步任务: ts_code={ts_code}, period={period}, type={type}, start_date={start_date}, end_date={end_date}")

        service = FinaMainbzService()
        result = run_async_in_celery(
            service.sync_fina_mainbz,
            ts_code=ts_code,
            period=period,
            type=type,
            start_date=start_date,
            end_date=end_date
        )

        if result["status"] == "success":
            logger.info(f"主营业务构成同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"主营业务构成同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行主营业务构成同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
