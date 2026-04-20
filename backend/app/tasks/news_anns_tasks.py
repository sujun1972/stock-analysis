"""公司公告同步 Celery 任务。

三个任务：
  - tasks.sync_stock_anns               增量（每日盘后或前端同步按钮触发）
  - tasks.sync_stock_anns_full_history  全量历史（按交易日切片 + Redis Set 续继）
  - tasks.sync_stock_anns_single        被动同步（单只股票）
"""

from __future__ import annotations

import traceback

from loguru import logger

from app.celery_app import celery_app
from app.tasks._task_factory import make_full_history_task, make_incremental_task
from app.tasks.extended_sync_tasks import run_async_in_celery


# ------------------------------------------------------------------
# 增量 & 全量（工厂生成）
# ------------------------------------------------------------------

sync_stock_anns_task = make_incremental_task(
    name="tasks.sync_stock_anns",
    service_path="app.services.news_anns.stock_anns_sync_service:StockAnnsSyncService",
    display_name="公司公告",
    # StockAnnsSyncService 的增量"原始方法"就是 sync_incremental 本身
    # （AkShare 接口无 ts_code/trade_date/ann_date 等业务参数），所以这里把 raw_sync_method
    # 也指回 sync_incremental，并只声明 start_date/end_date 作为 raw_param_names；
    # 任意一个非空即走 raw 路径（等价），全为空时走 sync_incremental（从 sync_configs 读回看窗口）
    raw_sync_method="sync_incremental",
    raw_param_names=("start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
    # AkShare 全市场接口单日 60~120s，一次增量（7 个交易日）预计 ~15 min，放宽超时
    soft_time_limit=3600,
    time_limit=4200,
)


sync_stock_anns_full_history_task = make_full_history_task(
    name="tasks.sync_stock_anns_full_history",
    service_path="app.services.news_anns.stock_anns_sync_service:StockAnnsSyncService",
    table_key="stock_anns",
    display_name="公司公告",
    # 全量按交易日并发拉，单日 ~90s × 1500 日 / 5 并发 ≈ 7.5 小时；
    # 前端可在 sync_configs 页面把起始日改为近 6 个月缩短到 ~1 小时
    soft_time_limit=36000,  # 10h
    time_limit=43200,       # 12h
    default_concurrency=5,
    accept_strategy_param=False,  # by_date 固定，不接收 strategy 参数
    accept_max_rpm=False,
)


# ------------------------------------------------------------------
# 被动同步（单只股票，签名不兼容工厂，单独实现）
# ------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="tasks.sync_stock_anns_single",
    max_retries=0,
    soft_time_limit=120,
    time_limit=150,
)
def sync_stock_anns_single_task(self, ts_code: str, days: int = 90):
    """单只股票公告被动同步（用户打开个股 AI 分析弹窗时触发）。"""
    from app.services.news_anns.stock_anns_sync_service import StockAnnsSyncService

    logger.info(f"[Celery] 被动同步公司公告 ts_code={ts_code} days={days}")
    try:
        service = StockAnnsSyncService()
        result = run_async_in_celery(service.sync_by_stock, ts_code=ts_code, days=int(days))
        if result.get("status") == "success":
            logger.info(f"被动同步公司公告成功 {ts_code}: {result.get('records', 0)} 条")
            return result
        error_msg = result.get("error") or "未知错误"
        logger.warning(f"被动同步公司公告失败 {ts_code}: {error_msg}")
        raise Exception(f"同步失败: {error_msg}")
    except Exception as exc:
        logger.error(f"被动同步公司公告异常 {ts_code}: {exc}")
        logger.error(traceback.format_exc())
        raise
