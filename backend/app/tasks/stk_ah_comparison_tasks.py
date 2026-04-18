"""AH股比价同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_ah_comparison_task = make_incremental_task(
    name="tasks.sync_stk_ah_comparison",
    service_path="app.services.stk_ah_comparison_service:StkAhComparisonService",
    display_name="AH股比价",
    raw_sync_method="sync_stk_ah_comparison",
    raw_param_names=("hk_code", "ts_code", "trade_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_stk_ah_comparison_full_history_task = make_full_history_task(
    name="tasks.sync_stk_ah_comparison_full_history",
    service_path="app.services.stk_ah_comparison_service:StkAhComparisonService",
    table_key="stk_ah_comparison",
    display_name="AH股比价",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
