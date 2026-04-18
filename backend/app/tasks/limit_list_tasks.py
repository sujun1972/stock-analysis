"""涨跌停列表同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_limit_list_task = make_incremental_task(
    name="tasks.sync_limit_list",
    service_path="app.services.limit_list_service:LimitListService",
    display_name="涨跌停列表",
    raw_sync_method="sync_limit_list",
    raw_param_names=("trade_date", "start_date", "end_date", "ts_code", "limit_type"),
)

sync_limit_list_full_history_task = make_full_history_task(
    name="tasks.sync_limit_list_full_history",
    service_path="app.services.limit_list_service:LimitListService",
    table_key="limit_list",
    display_name="涨跌停列表",
    soft_time_limit=7200,
    time_limit=10800,
)
