"""港股通每月成交统计同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_ggt_monthly_task = make_incremental_task(
    name="tasks.sync_ggt_monthly",
    service_path="app.services.ggt_monthly_service:GgtMonthlyService",
    display_name="港股通每月成交统计",
    raw_sync_method="sync_data",
    raw_param_names=("month", "start_month", "end_month"),
)

sync_ggt_monthly_full_history_task = make_full_history_task(
    name="tasks.sync_ggt_monthly_full_history",
    service_path="app.services.ggt_monthly_service:GgtMonthlyService",
    table_key="ggt_monthly",
    display_name="港股通每月成交统计",
    soft_time_limit=7200,
    time_limit=10800,
)
