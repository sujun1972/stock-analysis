"""业绩预告同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_forecast_task = make_incremental_task(
    name="tasks.sync_forecast",
    service_path="app.services.forecast_service:ForecastService",
    display_name="业绩预告",
    raw_sync_method="sync_forecast",
    raw_param_names=("ann_date", "start_date", "end_date", "period", "type_"),
)

sync_forecast_full_history_task = make_full_history_task(
    name="tasks.sync_forecast_full_history",
    service_path="app.services.forecast_service:ForecastService",
    table_key="forecast",
    display_name="业绩预告",
)
