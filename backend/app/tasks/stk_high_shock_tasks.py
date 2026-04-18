"""个股严重异常波动同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_high_shock_task = make_incremental_task(
    name="tasks.sync_stk_high_shock",
    service_path="app.services.stk_high_shock_service:StkHighShockService",
    display_name="个股严重异常波动",
    raw_sync_method="sync_stk_high_shock",
    raw_param_names=("trade_date", "start_date", "end_date", "ts_code"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_stk_high_shock_full_history_task = make_full_history_task(
    name="tasks.sync_stk_high_shock_full_history",
    service_path="app.services.stk_high_shock_service:StkHighShockService",
    table_key="stk_high_shock",
    display_name="个股严重异常波动",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
