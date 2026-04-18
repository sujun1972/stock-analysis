"""资产负债表同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_balancesheet_task = make_incremental_task(
    name="tasks.sync_balancesheet",
    service_path="app.services.balancesheet_service:BalancesheetService",
    display_name="资产负债表",
    raw_sync_method="sync_balancesheet",
    raw_param_names=("ts_code", "period", "start_date", "end_date", "report_type", "comp_type"),
)

sync_balancesheet_full_history_task = make_full_history_task(
    name="tasks.sync_balancesheet_full_history",
    service_path="app.services.balancesheet_service:BalancesheetService",
    table_key="balancesheet",
    display_name="资产负债表",
)
