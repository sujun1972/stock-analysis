"""沪深港股通持股明细同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_hk_hold_task = make_incremental_task(
    name="tasks.sync_hk_hold",
    service_path="app.services.hk_hold_service:HkHoldService",
    display_name="沪深港股通持股明细",
    raw_sync_method="sync_hk_hold",
    raw_param_names=("code", "ts_code", "trade_date", "start_date", "end_date", "exchange"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_hk_hold_full_history_task = make_full_history_task(
    name="tasks.sync_hk_hold_full_history",
    service_path="app.services.hk_hold_service:HkHoldService",
    table_key="hk_hold",
    display_name="沪深港股通持股明细",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
