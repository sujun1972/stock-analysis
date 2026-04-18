"""沪深股通十大成交股同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_hsgt_top10_task = make_incremental_task(
    name="tasks.sync_hsgt_top10",
    service_path="app.services.hsgt_top10_service:HsgtTop10Service",
    display_name="沪深股通十大成交股",
    raw_sync_method="sync_hsgt_top10",
    raw_param_names=("ts_code", "trade_date", "start_date", "end_date", "market_type"),
)

sync_hsgt_top10_full_history_task = make_full_history_task(
    name="tasks.sync_hsgt_top10_full_history",
    service_path="app.services.hsgt_top10_service:HsgtTop10Service",
    table_key="hsgt_top10",
    display_name="沪深股通十大成交股",
    soft_time_limit=14400,
    time_limit=18000,
)
