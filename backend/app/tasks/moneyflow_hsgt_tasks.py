"""
沪深港通资金流向同步任务

注意事项:
- 任务在 Celery fork pool worker 中执行
- 必须为每个任务创建独立的 asyncio 事件循环
- 执行完成后需要关闭事件循环释放资源
"""

from typing import Optional
from celery import current_task
from loguru import logger
import asyncio

from app.celery_app import celery_app
from app.services.extended_sync_service import ExtendedDataSyncService


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt")
def sync_moneyflow_hsgt_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    同步沪深港通资金流向数据

    Args:
        trade_date: 交易日期 YYYYMMDD
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行沪深港通资金流向同步任务: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

        service = ExtendedDataSyncService()

        # 在 Celery fork pool worker 中创建独立的事件循环
        # 避免复用可能已关闭的事件循环，防止 "Event loop is closed" 错误
        try:
            old_loop = asyncio.get_event_loop()
            if not old_loop.is_closed():
                old_loop.close()
        except RuntimeError:
            pass

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                service.sync_moneyflow_hsgt(
                    trade_date=trade_date,
                    start_date=start_date,
                    end_date=end_date
                )
            )

            if result["status"] == "success":
                logger.info(f"沪深港通资金流向同步成功: {result['records']} 条")
                return result
            else:
                logger.warning(f"沪深港通资金流向同步失败: {result}")
                error_msg = result.get('error', '未知错误')
                raise Exception(f"同步失败: {error_msg}")

        finally:
            # 关闭事件循环释放资源
            try:
                loop.close()
            except Exception as e:
                logger.warning(f"关闭事件循环时出错: {e}")

    except Exception as e:
        logger.error(f"执行沪深港通资金流向同步任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt_daily")
def sync_moneyflow_hsgt_daily_task(self):
    """
    每日定时同步沪深港通资金流向数据

    Returns:
        同步结果
    """
    try:
        logger.info("开始执行每日沪深港通资金流向同步任务")

        # 不指定日期，让服务自动获取最新交易日
        return sync_moneyflow_hsgt_task.apply_async(
            args=[],
            kwargs={'trade_date': None, 'start_date': None, 'end_date': None}
        ).get()

    except Exception as e:
        logger.error(f"执行每日沪深港通资金流向同步任务失败: {str(e)}")
        raise


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt_range")
def sync_moneyflow_hsgt_range_task(
    self,
    start_date: str,
    end_date: str
):
    """
    同步指定日期范围的沪深港通资金流向数据

    Args:
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD

    Returns:
        同步结果
    """
    try:
        logger.info(f"开始执行沪深港通资金流向范围同步任务: {start_date} - {end_date}")

        return sync_moneyflow_hsgt_task.apply_async(
            args=[],
            kwargs={'trade_date': None, 'start_date': start_date, 'end_date': end_date}
        ).get()

    except Exception as e:
        logger.error(f"执行沪深港通资金流向范围同步任务失败: {str(e)}")
        raise