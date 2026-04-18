"""交易所重点提示证券同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_alert_task = make_incremental_task(
    name="tasks.sync_stk_alert",
    service_path="app.services.stk_alert_service:StkAlertService",
    display_name="交易所重点提示证券",
    raw_sync_method="sync_stk_alert",
    raw_param_names=("trade_date", "start_date", "end_date", "ts_code"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_stk_alert_full_history_task = make_full_history_task(
    name="tasks.sync_stk_alert_full_history",
    service_path="app.services.stk_alert_service:StkAlertService",
    table_key="stk_alert",
    display_name="交易所重点提示证券",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
