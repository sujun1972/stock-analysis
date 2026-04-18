"""财务审计意见同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_fina_audit_task = make_incremental_task(
    name="tasks.sync_fina_audit",
    service_path="app.services.fina_audit_service:FinaAuditService",
    display_name="财务审计意见",
    raw_sync_method="sync_fina_audit",
    raw_param_names=("ts_code", "ann_date", "start_date", "end_date", "period"),
)

sync_fina_audit_full_history_task = make_full_history_task(
    name="tasks.sync_fina_audit_full_history",
    service_path="app.services.fina_audit_service:FinaAuditService",
    table_key="fina_audit",
    display_name="财务审计意见",
)
