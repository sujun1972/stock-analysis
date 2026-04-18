"""每日涨跌停价格同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stk_limit_d_incremental_task = make_incremental_task(
    name="tasks.sync_stk_limit_d_incremental",
    service_path="app.services.stk_limit_d_service:StkLimitDService",
    display_name="每日涨跌停价格",
    raw_sync_method="sync_incremental",
    raw_param_names=(),
    incremental_extra_kwargs=("start_date", "end_date", "sync_strategy", "max_requests_per_minute"),
    max_retries=2,
    retry_backoff=180,
    retry_jitter=True,
)

sync_stk_limit_d_full_history_task = make_full_history_task(
    name="tasks.sync_stk_limit_d_full_history",
    service_path="app.services.stk_limit_d_service:StkLimitDService",
    table_key="stk_limit_d",
    display_name="每日涨跌停价格",
    default_concurrency=3,
    default_strategy="by_ts_code",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
