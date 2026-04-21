"""新闻资讯 & 公司公告同步 Celery 任务。

Phase 1（公司公告）：
  - tasks.sync_stock_anns               增量（每日盘后或前端同步按钮触发）
  - tasks.sync_stock_anns_full_history  全量历史（按交易日切片 + Redis Set 续继）
  - tasks.sync_stock_anns_single        被动同步（单只股票）

Phase 2（财经快讯 + 新闻联播）：
  - tasks.sync_news_flash               财新要闻精选（拉最近 ~100 条，无日期参数）
  - tasks.sync_news_flash_full_history  同 sync_news_flash（无历史参数，兼容按钮）
  - tasks.sync_news_flash_single        单只股票被动同步（东财个股新闻）
  - tasks.sync_cctv_news                新闻联播增量（逐日 + 回看 N 天）
  - tasks.sync_cctv_news_full_history   新闻联播全量（按日并发 + Redis Set 续继）

Phase 3（宏观经济指标）：
  - tasks.sync_macro_indicators               增量（CPI/PPI/PMI/M2/新增社融/GDP/Shibor，全历史 UPSERT）
  - tasks.sync_macro_indicators_full_history  同 sync_macro_indicators（AkShare 接口无日期参数）

Phase 5（舆情情绪打分）：
  - tasks.score_stock_anns_sentiment   公告批量打分（每次 30 条，未打分的按 ann_date 降序）
  - tasks.score_news_flash_sentiment   快讯批量打分（每次 30 条，related_ts_codes 非空）
  两个任务可同步完成后由 Service 层触发，也可定时扫尾。
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


# ==================================================================
# Phase 2: 财经快讯 + 新闻联播
# ==================================================================

# ------------------------------------------------------------------
# 财经快讯（财新要闻精选，无日期参数）
# ------------------------------------------------------------------

sync_news_flash_task = make_incremental_task(
    name="tasks.sync_news_flash",
    service_path="app.services.news_anns.news_flash_sync_service:NewsFlashSyncService",
    display_name="财经快讯",
    raw_sync_method="sync_incremental",
    raw_param_names=("start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
    # 财新接口单次 1-2s，高频触发（如每 5 分钟）很轻量
    soft_time_limit=300,
    time_limit=360,
)


sync_news_flash_full_history_task = make_full_history_task(
    name="tasks.sync_news_flash_full_history",
    service_path="app.services.news_anns.news_flash_sync_service:NewsFlashSyncService",
    table_key="news_flash",
    display_name="财经快讯",
    # AkShare 快讯接口不支持历史参数，sync_full_history 退化为一次增量；按钮兼容
    soft_time_limit=300,
    time_limit=360,
    default_concurrency=1,
    accept_strategy_param=False,
    accept_max_rpm=False,
)


@celery_app.task(
    bind=True,
    name="tasks.sync_news_flash_single",
    max_retries=0,
    soft_time_limit=90,
    time_limit=120,
)
def sync_news_flash_single_task(self, ts_code: str, days: int = 7):
    """单只股票被动同步东财个股新闻（打开个股 AI 分析弹窗时触发）。"""
    from app.services.news_anns.news_flash_sync_service import NewsFlashSyncService

    logger.info(f"[Celery] 被动同步个股新闻 ts_code={ts_code} days={days}")
    try:
        service = NewsFlashSyncService()
        result = run_async_in_celery(service.sync_by_stock, ts_code=ts_code, days=int(days))
        if result.get("status") == "success":
            logger.info(f"被动同步个股新闻成功 {ts_code}: {result.get('records', 0)} 条")
            return result
        error_msg = result.get("error") or "未知错误"
        logger.warning(f"被动同步个股新闻失败 {ts_code}: {error_msg}")
        raise Exception(f"同步失败: {error_msg}")
    except Exception as exc:
        logger.error(f"被动同步个股新闻异常 {ts_code}: {exc}")
        logger.error(traceback.format_exc())
        raise


# ------------------------------------------------------------------
# 新闻联播（按自然日）
# ------------------------------------------------------------------

sync_cctv_news_task = make_incremental_task(
    name="tasks.sync_cctv_news",
    service_path="app.services.news_anns.cctv_news_sync_service:CctvNewsSyncService",
    display_name="新闻联播",
    raw_sync_method="sync_incremental",
    raw_param_names=("start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
    # 单日 3-8s，回看 3 天 ≈ 30s 内
    soft_time_limit=900,
    time_limit=1200,
)


sync_cctv_news_full_history_task = make_full_history_task(
    name="tasks.sync_cctv_news_full_history",
    service_path="app.services.news_anns.cctv_news_sync_service:CctvNewsSyncService",
    table_key="cctv_news",
    display_name="新闻联播",
    # 按日并发 1，1500 天 × 8s ≈ 3 小时；Redis Set 续继可中断恢复
    soft_time_limit=21600,  # 6h
    time_limit=25200,       # 7h
    default_concurrency=1,
    accept_strategy_param=False,
    accept_max_rpm=False,
)


# ==================================================================
# Phase 3: 宏观经济指标
# ==================================================================

# AkShare 宏观接口无日期参数，每次拉完整历史序列并 UPSERT；7 个接口串行约 2-3 分钟。
# 增量与"全量"同路径（接口能力所限），两个 task 共享同一 Service 入口。

sync_macro_indicators_task = make_incremental_task(
    name="tasks.sync_macro_indicators",
    service_path="app.services.news_anns.macro_sync_service:MacroSyncService",
    display_name="宏观经济指标",
    raw_sync_method="sync_incremental",
    raw_param_names=("start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
    # 7 个接口串行，单个 10-30s，留宽裕超时
    soft_time_limit=900,
    time_limit=1200,
)


sync_macro_indicators_full_history_task = make_full_history_task(
    name="tasks.sync_macro_indicators_full_history",
    service_path="app.services.news_anns.macro_sync_service:MacroSyncService",
    table_key="macro_indicators",
    display_name="宏观经济指标",
    # AkShare 宏观接口无历史参数，sync_full_history 退化为单次增量
    soft_time_limit=900,
    time_limit=1200,
    default_concurrency=1,
    accept_strategy_param=False,
    accept_max_rpm=False,
)


# ==================================================================
# Phase 5: 舆情情绪打分
# ==================================================================

# 单次批量 30 条，LLM 调用 5-20s；定时 30min 扫一次尾，同步后可主动触发
_SENTIMENT_BATCH_SIZE = 30


@celery_app.task(
    bind=True,
    name="tasks.score_stock_anns_sentiment",
    max_retries=0,
    soft_time_limit=300,
    time_limit=360,
)
def score_stock_anns_sentiment_task(self, limit: int = _SENTIMENT_BATCH_SIZE, provider: str = None):
    """公告舆情批量打分（事件标签 + 情绪 + 影响方向）。"""
    from app.services.news_anns.sentiment_scoring_service import get_sentiment_scoring_service

    logger.info(f"[Celery] 公告舆情打分 limit={limit} provider={provider}")
    try:
        service = get_sentiment_scoring_service()
        return run_async_in_celery(service.run_batch_anns, limit=int(limit), provider=provider)
    except Exception as exc:
        logger.error(f"公告舆情打分异常: {exc}")
        logger.error(traceback.format_exc())
        raise


@celery_app.task(
    bind=True,
    name="tasks.score_news_flash_sentiment",
    max_retries=0,
    soft_time_limit=300,
    time_limit=360,
)
def score_news_flash_sentiment_task(self, limit: int = _SENTIMENT_BATCH_SIZE, provider: str = None):
    """快讯舆情批量打分（情绪 + 主题标签；仅 related_ts_codes 非空）。"""
    from app.services.news_anns.sentiment_scoring_service import get_sentiment_scoring_service

    logger.info(f"[Celery] 快讯舆情打分 limit={limit} provider={provider}")
    try:
        service = get_sentiment_scoring_service()
        return run_async_in_celery(service.run_batch_news, limit=int(limit), provider=provider)
    except Exception as exc:
        logger.error(f"快讯舆情打分异常: {exc}")
        logger.error(traceback.format_exc())
        raise
