"""最强板块统计同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_limit_cpt_task = make_incremental_task(
    name="tasks.sync_limit_cpt",
    service_path="app.services.limit_cpt_service:LimitCptService",
    display_name="最强板块统计",
    raw_sync_method="sync_limit_cpt",
    raw_param_names=("trade_date", "ts_code", "start_date", "end_date"),
)

sync_limit_cpt_full_history_task = make_full_history_task(
    name="tasks.sync_limit_cpt_full_history",
    service_path="app.services.limit_cpt_service:LimitCptService",
    table_key="limit_cpt",
    display_name="最强板块统计",
    soft_time_limit=7200,
    time_limit=10800,
)
