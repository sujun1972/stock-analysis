"""龙虎榜每日明细同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_top_list_task = make_incremental_task(
    name="tasks.sync_top_list",
    service_path="app.services.top_list_service:TopListService",
    display_name="龙虎榜",
    raw_sync_method="sync_top_list",
    raw_param_names=("trade_date", "ts_code"),
)

sync_top_list_full_history_task = make_full_history_task(
    name="tasks.sync_top_list_full_history",
    service_path="app.services.top_list_service:TopListService",
    table_key="top_list",
    display_name="龙虎榜",
    soft_time_limit=7200,
    time_limit=10800,
)
