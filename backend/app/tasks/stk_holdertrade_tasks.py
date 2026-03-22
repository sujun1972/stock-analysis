"""
股东增减持同步任务

使用 run_async_in_celery 处理 Celery fork pool 中的事件循环冲突问题
"""

from typing import Optional
from loguru import logger

from app.celery_app import celery_app
from app.services.stk_holdertrade_service import StkHoldertradeService
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_stk_holdertrade")
def sync_stk_holdertrade_task(
    self,
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    trade_type: Optional[str] = None,
    holder_type: Optional[str] = None
):
    """
    同步股东增减持数据

    Args:
        ts_code: 股票代码
        ann_date: 公告日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
        trade_type: 交易类型 IN=增持 DE=减持
        holder_type: 股东类型 G=高管 P=个人 C=公司

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行股东增减持同步任务: ts_code={ts_code}, ann_date={ann_date}, "
                   f"start_date={start_date}, end_date={end_date}, "
                   f"trade_type={trade_type}, holder_type={holder_type}")

        service = StkHoldertradeService()
        result = run_async_in_celery(
            service.sync_stk_holdertrade,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            trade_type=trade_type,
            holder_type=holder_type
        )

        if result["status"] == "success":
            logger.info(f"股东增减持同步成功: {result['records']} 条")
            return result
        else:
            logger.warning(f"股东增减持同步失败: {result}")
            error_msg = result.get('error', '未知错误')
            raise Exception(f"同步失败: {error_msg}")

    except Exception as e:
        logger.error(f"执行股东增减持同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise
