"""中央结算系统持股汇总同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_ccass_hold_task = make_incremental_task(
    name="tasks.sync_ccass_hold",
    service_path="app.services.ccass_hold_service:CcassHoldService",
    display_name="中央结算系统持股汇总",
    raw_sync_method="sync_ccass_hold",
    raw_param_names=("ts_code", "hk_code", "trade_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_ccass_hold_full_history_task = make_full_history_task(
    name="tasks.sync_ccass_hold_full_history",
    service_path="app.services.ccass_hold_service:CcassHoldService",
    table_key="ccass_hold",
    display_name="中央结算系统持股汇总",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
