"""
港股通十大成交股数据同步任务
"""

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.ggt_top10_service import GgtTop10Service
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_ggt_top10")
def sync_ggt_top10_task(
    self,
    ts_code: str = None,
    trade_date: str = None,
    start_date: str = None,
    end_date: str = None,
    market_type: str = None
):
    """
    同步港股通十大成交股数据

    Args:
        ts_code: 股票代码（可选）
        trade_date: 交易日期 YYYYMMDD（可选）
        start_date: 开始日期 YYYYMMDD（可选）
        end_date: 结束日期 YYYYMMDD（可选）
        market_type: 市场类型 2:港股通(沪) 4:港股通(深)（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行港股通十大成交股同步任务")
        logger.info(f"参数: ts_code={ts_code}, trade_date={trade_date}, "
                   f"start_date={start_date}, end_date={end_date}, market_type={market_type}")

        # 使用辅助函数运行异步代码
        service = GgtTop10Service()
        result = run_async_in_celery(
            service.sync_ggt_top10,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            market_type=market_type
        )

        logger.info(f"港股通十大成交股同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"港股通十大成交股同步任务失败: {e}")
        raise
