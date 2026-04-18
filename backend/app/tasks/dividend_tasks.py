"""分红送股同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_dividend_task = make_incremental_task(
    name="tasks.sync_dividend",
    service_path="app.services.dividend_service:DividendService",
    display_name="分红送股",
    raw_sync_method="sync_dividend",
    raw_param_names=("ts_code", "ann_date", "record_date", "ex_date", "imp_ann_date"),
)

sync_dividend_full_history_task = make_full_history_task(
    name="tasks.sync_dividend_full_history",
    service_path="app.services.dividend_service:DividendService",
    table_key="dividend",
    display_name="分红送股",
)
