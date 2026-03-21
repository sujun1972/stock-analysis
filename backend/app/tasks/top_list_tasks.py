"""
龙虎榜每日明细 Celery 任务
"""
from typing import Optional
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.top_list_service import TopListService
from loguru import logger


@celery_app.task(bind=True, name="tasks.sync_top_list")
def sync_top_list_task(
    self,
    trade_date: Optional[str] = None,
    ts_code: Optional[str] = None
):
    """
    同步龙虎榜每日明细数据

    Args:
        trade_date: 交易日期，格式：YYYYMMDD（可选，默认为当天）
        ts_code: 股票代码（可选）

    Returns:
        同步结果字典
    """
    try:
        logger.info(f"开始执行龙虎榜数据同步任务: trade_date={trade_date}, ts_code={ts_code}")

        # 使用辅助函数运行异步代码
        service = TopListService()
        result = run_async_in_celery(
            service.sync_top_list,
            trade_date=trade_date,
            ts_code=ts_code
        )

        logger.info(f"龙虎榜数据同步任务完成: {result}")
        return result

    except Exception as e:
        logger.error(f"龙虎榜数据同步任务失败: {e}")
        raise
