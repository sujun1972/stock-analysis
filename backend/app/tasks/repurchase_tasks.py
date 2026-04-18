"""股票回购同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_repurchase_task = make_incremental_task(
    name="tasks.sync_repurchase",
    service_path="app.services.repurchase_service:RepurchaseService",
    display_name="股票回购",
    raw_sync_method="sync_repurchase",
    raw_param_names=("ann_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_repurchase_full_history_task = make_full_history_task(
    name="tasks.sync_repurchase_full_history",
    service_path="app.services.repurchase_service:RepurchaseService",
    table_key="repurchase",
    display_name="股票回购",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
