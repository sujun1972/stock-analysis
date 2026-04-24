"""价值度量 Celery 任务（魔法公式 ROC/EY + 格雷厄姆内在价值）

三个任务：
  - tasks.recompute_value_metrics_single : 单只重算（被动同步/手动触发）
  - tasks.recompute_value_metrics_flush  : Beat 周期触发，捞 Redis dirty set 批量重算
  - tasks.recompute_value_metrics_all    : 全市场重算（日终兜底 / daily_basic / report_rc）
"""

from __future__ import annotations

from loguru import logger

from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery


@celery_app.task(bind=True, name="tasks.recompute_value_metrics_single", max_retries=0)
def recompute_value_metrics_single_task(self, ts_code: str):
    """单只股票重算（Service 内自行做数据缺失判定，缺失时跳过不写入）。"""
    from app.services.value_metrics import ValueMetricsService

    svc = ValueMetricsService()
    ok = run_async_in_celery(svc.recompute_one, ts_code)
    return {"ts_code": ts_code, "ok": bool(ok)}


@celery_app.task(bind=True, name="tasks.recompute_value_metrics_flush", max_retries=0)
def recompute_value_metrics_flush_task(self):
    """从 Redis dirty set 批量捞出脏股票重算。

    - Redis 不可用 → 返回 0
    - 捞空时快速返回，不惊扰数据库
    """
    from app.services.value_metrics import ValueMetricsService, ValueMetricsTrigger

    codes = ValueMetricsTrigger.pop_dirty_batch(max_size=5000)
    if not codes:
        return {"total": 0, "ok": 0, "skipped": 0, "failed": 0}
    svc = ValueMetricsService()
    result = run_async_in_celery(svc.recompute_batch, codes)
    logger.info(f"[value_metrics_flush] 处理 {len(codes)} 只股票: {result}")
    return result


@celery_app.task(
    bind=True,
    name="tasks.recompute_value_metrics_all",
    max_retries=0,
    soft_time_limit=1800,
    time_limit=2100,
)
def recompute_value_metrics_all_task(self, source: str = "manual"):
    """全市场重算（约 5000 只股票，单只 ~20ms SQL + 计算，估计 2~3 分钟完成）。"""
    from app.services.value_metrics import ValueMetricsService

    svc = ValueMetricsService()
    result = run_async_in_celery(svc.recompute_all)
    logger.info(f"[value_metrics_all] source={source} 结果: {result}")
    return result
