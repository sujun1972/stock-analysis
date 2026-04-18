"""神奇九转指标同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_nineturn_task = make_incremental_task(
    name="tasks.sync_stk_nineturn",
    service_path="app.services.stk_nineturn_service:StkNineturnService",
    display_name="神奇九转指标",
    raw_sync_method="sync_stk_nineturn",
    raw_param_names=("ts_code", "trade_date", "freq", "start_date", "end_date"),
    raw_param_defaults={"freq": "daily"},
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_stk_nineturn_full_history_task = make_full_history_task(
    name="tasks.sync_stk_nineturn_full_history",
    service_path="app.services.stk_nineturn_service:StkNineturnService",
    table_key="stk_nineturn",
    display_name="神奇九转指标",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
