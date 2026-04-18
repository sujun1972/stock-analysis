"""港股通每日成交统计同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_ggt_daily_task = make_incremental_task(
    name="tasks.sync_ggt_daily",
    service_path="app.services.ggt_daily_service:GgtDailyService",
    display_name="港股通每日成交统计",
    raw_sync_method="sync_data",
    raw_param_names=("trade_date", "start_date", "end_date"),
)

sync_ggt_daily_full_history_task = make_full_history_task(
    name="tasks.sync_ggt_daily_full_history",
    service_path="app.services.ggt_daily_service:GgtDailyService",
    table_key="ggt_daily",
    display_name="港股通每日成交统计",
    soft_time_limit=7200,
    time_limit=10800,
    default_concurrency=3,
)
