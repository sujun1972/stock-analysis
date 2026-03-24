"""
沪深股通十大成交股同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.hsgt_top10_service import HsgtTop10Service
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_hsgt_top10")
def sync_hsgt_top10_task(
    self,
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    market_type: Optional[str] = None
):
    """
    同步沪深股通十大成交股数据

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        market_type: 市场类型 1:沪市 3:深市（可选）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行沪深股通十大成交股同步任务: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

        service = HsgtTop10Service()
        result = run_async_in_celery(
            service.sync_hsgt_top10,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )

        if result["status"] == "success":
            logger.info(f"沪深股通十大成交股同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"沪深股通十大成交股同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行沪深股通十大成交股同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
