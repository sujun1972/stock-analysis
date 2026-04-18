"""每日指标同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_daily_basic_incremental_task = make_incremental_task(
    name="tasks.sync_daily_basic_incremental",
    service_path="app.services.daily_basic_service:DailyBasicService",
    display_name="每日指标",
    raw_sync_method="sync_incremental",
    raw_param_names=(),
    incremental_extra_kwargs=("start_date", "end_date", "sync_strategy", "max_requests_per_minute"),
    max_retries=2,
    retry_backoff=180,
    retry_jitter=True,
)

sync_daily_basic_full_history_task = make_full_history_task(
    name="tasks.sync_daily_basic_full_history",
    service_path="app.services.daily_basic_service:DailyBasicService",
    table_key="daily_basic",
    display_name="每日指标",
    default_concurrency=8,
    default_strategy="by_ts_code",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
