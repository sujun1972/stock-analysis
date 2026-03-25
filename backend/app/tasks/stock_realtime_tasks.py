"""
实时行情同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional, List
from loguru import logger

from app.celery_app import celery_app
from app.services.stock_realtime_service import StockRealtimeService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_realtime_quotes")
def sync_realtime_quotes_task(
    self,
    codes: Optional[List[str]] = None,
    batch_size: Optional[int] = 100,
    update_oldest: bool = False,
    data_source: str = 'akshare'
):
    """
    同步实时行情数据

    Args:
        codes: 股票代码列表（None表示全部）
        batch_size: 批次大小
        update_oldest: 是否优先更新最旧的数据
        data_source: 数据源（akshare 或 tushare）

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行实时行情同步任务: codes={codes}, batch_size={batch_size}, "
                   f"update_oldest={update_oldest}, data_source={data_source}")

        service = StockRealtimeService()
        result = run_async_in_celery(
            service.sync_realtime_quotes,
            codes=codes,
            batch_size=batch_size,
            update_oldest=update_oldest,
            data_source=data_source
        )

        if result["status"] in ["success", "partial_success"]:
            logger.info(f"实时行情同步完成: {result['total']} 条")
            return result
        else:
            logger.warning(f"实时行情同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行实时行情同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
