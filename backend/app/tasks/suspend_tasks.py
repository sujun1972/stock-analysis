"""停复牌信息同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_suspend_task = make_incremental_task(
    name="tasks.sync_suspend",
    service_path="app.services.suspend_service:SuspendService",
    display_name="停复牌信息",
    raw_sync_method="sync_suspend",
    raw_param_names=("ts_code", "trade_date", "start_date", "end_date", "suspend_type"),
)

sync_suspend_full_history_task = make_full_history_task(
    name="tasks.sync_suspend_full_history",
    service_path="app.services.suspend_service:SuspendService",
    table_key="suspend",
    display_name="停复牌信息",
    accept_start_date_param=False,
)
