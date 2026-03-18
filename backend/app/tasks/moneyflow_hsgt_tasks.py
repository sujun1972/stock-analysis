"""
沪深港通资金流向同步任务
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

        # 创建服务实例
        service = ExtendedDataSyncService()

        # 执行同步（使用asyncio运行异步方法）
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

            # 更新任务状态
            if result["status"] == "success":
                logger.info(f"沪深港通资金流向同步成功: {result['records']} 条")
                current_task.update_state(
                    state='SUCCESS',
                    meta={
                        'current': 100,
                        'total': 100,
                        'status': '同步完成',
                        'records': result['records']
                    }
                )
            else:
                logger.warning(f"沪深港通资金流向同步失败: {result}")
                current_task.update_state(
                    state='FAILURE',
                    meta={
                        'current': 0,
                        'total': 100,
                        'status': '同步失败',
                        'error': result.get('error', '未知错误')
                    }
                )

            return result

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"执行沪深港通资金流向同步任务失败: {str(e)}")
        current_task.update_state(
            state='FAILURE',
            meta={
                'current': 0,
                'total': 100,
                'status': '任务失败',
                'error': str(e)
            }
        )
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