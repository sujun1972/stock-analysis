"""股东增减持同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_holdertrade_task = make_incremental_task(
    name="tasks.sync_stk_holdertrade",
    service_path="app.services.stk_holdertrade_service:StkHoldertradeService",
    display_name="股东增减持",
    raw_sync_method="sync_stk_holdertrade",
    raw_param_names=("ts_code", "ann_date", "start_date", "end_date", "trade_type", "holder_type"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_stk_holdertrade_full_history_task = make_full_history_task(
    name="tasks.sync_stk_holdertrade_full_history",
    service_path="app.services.stk_holdertrade_service:StkHoldertradeService",
    table_key="stk_holdertrade",
    display_name="股东增减持",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
