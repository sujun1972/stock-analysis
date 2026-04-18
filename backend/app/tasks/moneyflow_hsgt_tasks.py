"""沪深港通资金流向同步任务

增量任务保留手写实现：raw 路径委托给独立的 ``MoneyflowSyncService``，
不符合工厂"raw 与 incremental 共用同一 Service"的假设。
全量历史任务由工厂生成。
"""

from typing import Optional

from loguru import logger

from app.celery_app import celery_app
from app.tasks._task_factory import make_full_history_task
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt")
def sync_moneyflow_hsgt_task(
    self,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """同步沪深港通资金流向数据。"""
    logger.info(
        f"开始执行沪深港通资金流向同步任务: trade_date={trade_date}, "
        f"start_date={start_date}, end_date={end_date}"
    )
    from app.services.moneyflow_hsgt_service import MoneyflowHsgtService
    service = MoneyflowHsgtService()

    if not any([trade_date, start_date, end_date]):
        result = run_async_in_celery(service.sync_incremental)
    else:
        from app.services.extended_sync.moneyflow_sync import MoneyflowSyncService
        sync_service = MoneyflowSyncService()
        result = run_async_in_celery(
            sync_service.sync_moneyflow_hsgt,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
        )

    if result["status"] == "success":
        logger.info(f"沪深港通资金流向同步成功: {result['records']} 条")
        return result
    error_msg = result.get("error", "未知错误")
    logger.warning(f"沪深港通资金流向同步失败: {result}")
    raise Exception(f"同步失败: {error_msg}")


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt_daily")
def sync_moneyflow_hsgt_daily_task(self):
    """每日定时同步沪深港通资金流向数据。"""
    logger.info("开始执行每日沪深港通资金流向同步任务")
    return sync_moneyflow_hsgt_task.apply_async(
        args=[],
        kwargs={"trade_date": None, "start_date": None, "end_date": None},
    ).get()


@celery_app.task(bind=True, name="tasks.sync_moneyflow_hsgt_range")
def sync_moneyflow_hsgt_range_task(self, start_date: str, end_date: str):
    """同步指定日期范围的沪深港通资金流向数据。"""
    logger.info(f"开始执行沪深港通资金流向范围同步任务: {start_date} - {end_date}")
    return sync_moneyflow_hsgt_task.apply_async(
        args=[],
        kwargs={"trade_date": None, "start_date": start_date, "end_date": end_date},
    ).get()


sync_moneyflow_hsgt_full_history_task = make_full_history_task(
    name="tasks.sync_moneyflow_hsgt_full_history",
    service_path="app.services.moneyflow_hsgt_service:MoneyflowHsgtService",
    table_key="moneyflow_hsgt",
    display_name="沪深港通资金流向",
    soft_time_limit=7200,
    time_limit=10800,
)
