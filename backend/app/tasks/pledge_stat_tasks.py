"""股权质押统计同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_pledge_stat_task = make_incremental_task(
    name="tasks.sync_pledge_stat",
    service_path="app.services.pledge_stat_service:PledgeStatService",
    display_name="股权质押统计",
    raw_sync_method="sync_pledge_stat",
    raw_param_names=("trade_date", "start_date", "end_date", "ts_code"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_pledge_stat_full_history_task = make_full_history_task(
    name="tasks.sync_pledge_stat_full_history",
    service_path="app.services.pledge_stat_service:PledgeStatService",
    table_key="pledge_stat",
    display_name="股权质押统计",
    soft_time_limit=10800,
    time_limit=14400,
    default_strategy="by_ts_code",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
