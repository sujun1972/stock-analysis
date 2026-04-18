"""财报披露计划同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_disclosure_date_task = make_incremental_task(
    name="tasks.sync_disclosure_date",
    service_path="app.services.disclosure_date_service:DisclosureDateService",
    display_name="财报披露计划",
    raw_sync_method="sync_disclosure_date",
    raw_param_names=("ts_code", "end_date", "pre_date", "ann_date", "actual_date"),
)

sync_disclosure_date_full_history_task = make_full_history_task(
    name="tasks.sync_disclosure_date_full_history",
    service_path="app.services.disclosure_date_service:DisclosureDateService",
    table_key="disclosure_date",
    display_name="财报披露计划",
    accept_concurrency_param=False,
)
