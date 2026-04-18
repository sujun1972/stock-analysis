"""复权因子同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_adj_factor_task = make_incremental_task(
    name="tasks.sync_adj_factor",
    service_path="app.services.adj_factor_service:AdjFactorService",
    display_name="复权因子",
    raw_sync_method="sync_incremental",
    raw_param_names=(),
    incremental_extra_kwargs=(
        "ts_code", "trade_date", "start_date", "end_date",
        "sync_strategy", "max_requests_per_minute",
    ),
)

sync_adj_factor_full_history_task = make_full_history_task(
    name="tasks.sync_adj_factor_full_history",
    service_path="app.services.adj_factor_service:AdjFactorService",
    table_key="adj_factor",
    display_name="复权因子",
    default_concurrency=8,
    default_strategy="by_ts_code",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
