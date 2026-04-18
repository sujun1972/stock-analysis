"""连板天梯同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_limit_step_task = make_incremental_task(
    name="tasks.sync_limit_step",
    service_path="app.services.limit_step_service:LimitStepService",
    display_name="连板天梯",
    raw_sync_method="sync_limit_step",
    raw_param_names=("trade_date", "start_date", "end_date", "ts_code", "nums"),
)

sync_limit_step_full_history_task = make_full_history_task(
    name="tasks.sync_limit_step_full_history",
    service_path="app.services.limit_step_service:LimitStepService",
    table_key="limit_step",
    display_name="连板天梯",
    soft_time_limit=7200,
    time_limit=10800,
)
