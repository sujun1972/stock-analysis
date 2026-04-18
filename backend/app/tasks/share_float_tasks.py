"""限售股解禁同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_share_float_task = make_incremental_task(
    name="tasks.sync_share_float",
    service_path="app.services.share_float_service:ShareFloatService",
    display_name="限售股解禁",
    raw_sync_method="sync_share_float",
    raw_param_names=("ts_code", "ann_date", "float_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_share_float_full_history_task = make_full_history_task(
    name="tasks.sync_share_float_full_history",
    service_path="app.services.share_float_service:ShareFloatService",
    table_key="share_float",
    display_name="限售股解禁",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
