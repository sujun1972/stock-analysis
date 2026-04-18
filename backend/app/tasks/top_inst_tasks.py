"""龙虎榜机构明细同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_top_inst_task = make_incremental_task(
    name="tasks.sync_top_inst",
    service_path="app.services.top_inst_service:TopInstService",
    display_name="龙虎榜机构明细",
    raw_sync_method="sync_top_inst",
    raw_param_names=("trade_date", "ts_code"),
)

sync_top_inst_full_history_task = make_full_history_task(
    name="tasks.sync_top_inst_full_history",
    service_path="app.services.top_inst_service:TopInstService",
    table_key="top_inst",
    display_name="龙虎榜机构明细",
    soft_time_limit=7200,
    time_limit=10800,
)
