"""融资融券交易明细同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_margin_detail_task = make_incremental_task(
    name="tasks.sync_margin_detail",
    service_path="app.services.margin_detail_service:MarginDetailService",
    display_name="融资融券交易明细",
    raw_sync_method="sync_margin_detail",
    raw_param_names=("trade_date", "ts_code", "start_date", "end_date"),
)

sync_margin_detail_full_history_task = make_full_history_task(
    name="tasks.sync_margin_detail_full_history",
    service_path="app.services.margin_detail_service:MarginDetailService",
    table_key="margin_detail",
    display_name="融资融券交易明细",
    soft_time_limit=7200,
    time_limit=10800,
)
