"""利润表同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_income_task = make_incremental_task(
    name="tasks.sync_income",
    service_path="app.services.income_service:IncomeService",
    display_name="利润表",
    raw_sync_method="sync_income",
    raw_param_names=("ts_code", "period", "start_date", "end_date", "report_type"),
)

sync_income_full_history_task = make_full_history_task(
    name="tasks.sync_income_full_history",
    service_path="app.services.income_service:IncomeService",
    table_key="income",
    display_name="利润表",
)
