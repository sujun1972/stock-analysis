"""每日筹码分布同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_cyq_chips_task = make_incremental_task(
    name="tasks.sync_cyq_chips",
    service_path="app.services.cyq_chips_service:CyqChipsService",
    display_name="每日筹码分布",
    raw_sync_method="sync_cyq_chips",
    raw_param_names=("ts_code", "trade_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_cyq_chips_full_history_task = make_full_history_task(
    name="tasks.sync_cyq_chips_full_history",
    service_path="app.services.cyq_chips_service:CyqChipsService",
    table_key="cyq_chips",
    display_name="每日筹码分布",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_ts_code",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
