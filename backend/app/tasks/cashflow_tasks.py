"""现金流量表同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_cashflow_task = make_incremental_task(
    name="tasks.sync_cashflow",
    service_path="app.services.cashflow_service:CashflowService",
    display_name="现金流量表",
    raw_sync_method="sync_cashflow",
    raw_param_names=("ts_code", "start_date", "end_date", "period", "report_type"),
)

sync_cashflow_full_history_task = make_full_history_task(
    name="tasks.sync_cashflow_full_history",
    service_path="app.services.cashflow_service:CashflowService",
    table_key="cashflow",
    display_name="现金流量表",
)
