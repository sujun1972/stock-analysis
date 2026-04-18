"""主营业务构成同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_fina_mainbz_task = make_incremental_task(
    name="tasks.sync_fina_mainbz",
    service_path="app.services.fina_mainbz_service:FinaMainbzService",
    display_name="主营业务构成",
    raw_sync_method="sync_fina_mainbz",
    raw_param_names=("ts_code", "period", "type", "start_date", "end_date"),
)

sync_fina_mainbz_full_history_task = make_full_history_task(
    name="tasks.sync_fina_mainbz_full_history",
    service_path="app.services.fina_mainbz_service:FinaMainbzService",
    table_key="fina_mainbz",
    display_name="主营业务构成",
)
