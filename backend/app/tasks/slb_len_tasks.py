"""转融资交易汇总同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_slb_len_task = make_incremental_task(
    name="tasks.sync_slb_len",
    service_path="app.services.slb_len_service:SlbLenService",
    display_name="转融资交易汇总",
    raw_sync_method="sync_slb_len",
    raw_param_names=("trade_date", "start_date", "end_date"),
)

sync_slb_len_full_history_task = make_full_history_task(
    name="tasks.sync_slb_len_full_history",
    service_path="app.services.slb_len_service:SlbLenService",
    table_key="slb_len",
    display_name="转融资交易汇总",
    soft_time_limit=7200,
    time_limit=10800,
)
