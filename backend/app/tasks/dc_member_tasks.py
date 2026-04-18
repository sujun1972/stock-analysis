"""东方财富板块成分同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_dc_member_task = make_incremental_task(
    name="tasks.sync_dc_member",
    service_path="app.services.dc_member_service:DcMemberService",
    display_name="东方财富板块成分",
    raw_sync_method="sync_dc_member",
    raw_param_names=("ts_code", "con_code", "trade_date", "start_date", "end_date"),
)

sync_dc_member_full_history_task = make_full_history_task(
    name="tasks.sync_dc_member_full_history",
    service_path="app.services.dc_member_service:DcMemberService",
    table_key="dc_member",
    display_name="东方财富板块成分",
    soft_time_limit=7200,
    time_limit=10800,
)
