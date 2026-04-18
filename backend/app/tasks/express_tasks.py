"""业绩快报同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_express_task = make_incremental_task(
    name="tasks.sync_express",
    service_path="app.services.express_service:ExpressService",
    display_name="业绩快报",
    raw_sync_method="sync_express",
    raw_param_names=("ts_code", "ann_date", "start_date", "end_date", "period"),
)

sync_express_full_history_task = make_full_history_task(
    name="tasks.sync_express_full_history",
    service_path="app.services.express_service:ExpressService",
    table_key="express",
    display_name="业绩快报",
)
