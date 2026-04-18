"""东方财富概念板块行情同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_dc_daily_task = make_incremental_task(
    name="tasks.sync_dc_daily",
    service_path="app.services.dc_daily_service:DcDailyService",
    display_name="东方财富概念板块行情",
    raw_sync_method="sync_dc_daily",
    raw_param_names=("ts_code", "trade_date", "start_date", "end_date", "idx_type"),
)

sync_dc_daily_full_history_task = make_full_history_task(
    name="tasks.sync_dc_daily_full_history",
    service_path="app.services.dc_daily_service:DcDailyService",
    table_key="dc_daily",
    display_name="东方财富概念板块行情",
    soft_time_limit=7200,
    time_limit=10800,
)
