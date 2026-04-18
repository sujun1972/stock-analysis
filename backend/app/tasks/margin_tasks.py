"""融资融券交易汇总同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_margin_task = make_incremental_task(
    name="tasks.sync_margin",
    service_path="app.services.margin_service:MarginService",
    display_name="融资融券交易汇总",
    raw_sync_method="sync_margin",
    raw_param_names=("trade_date", "start_date", "end_date", "exchange_id"),
)

sync_margin_full_history_task = make_full_history_task(
    name="tasks.sync_margin_full_history",
    service_path="app.services.margin_service:MarginService",
    table_key="margin",
    display_name="融资融券交易汇总",
    soft_time_limit=7200,
    time_limit=10800,
)
