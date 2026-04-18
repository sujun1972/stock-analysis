"""卖方盈利预测同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_report_rc_task = make_incremental_task(
    name="tasks.sync_report_rc",
    service_path="app.services.report_rc_service:ReportRcService",
    display_name="卖方盈利预测",
    raw_sync_method="sync_report_rc",
    raw_param_names=("ts_code", "report_date", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_report_rc_full_history_task = make_full_history_task(
    name="tasks.sync_report_rc_full_history",
    service_path="app.services.report_rc_service:ReportRcService",
    table_key="report_rc",
    display_name="卖方盈利预测",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
