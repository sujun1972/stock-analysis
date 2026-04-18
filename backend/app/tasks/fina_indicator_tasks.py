"""财务指标同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_fina_indicator_task = make_incremental_task(
    name="tasks.sync_fina_indicator",
    service_path="app.services.fina_indicator_service:FinaIndicatorService",
    display_name="财务指标",
    raw_sync_method="sync_fina_indicator",
    raw_param_names=("ts_code", "ann_date", "start_date", "end_date", "period"),
)

sync_fina_indicator_full_history_task = make_full_history_task(
    name="tasks.sync_fina_indicator_full_history",
    service_path="app.services.fina_indicator_service:FinaIndicatorService",
    table_key="fina_indicator",
    display_name="财务指标",
)
