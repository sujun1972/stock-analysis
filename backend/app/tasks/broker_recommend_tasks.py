"""券商每月荐股同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_broker_recommend_task = make_incremental_task(
    name="tasks.sync_broker_recommend",
    service_path="app.services.broker_recommend_service:BrokerRecommendService",
    display_name="券商每月荐股",
    raw_sync_method="sync_broker_recommend",
    raw_param_names=("month",),
    incremental_extra_kwargs=("max_requests_per_minute",),
)

sync_broker_recommend_full_history_task = make_full_history_task(
    name="tasks.sync_broker_recommend_full_history",
    service_path="app.services.broker_recommend_service:BrokerRecommendService",
    table_key="broker_recommend",
    display_name="券商每月荐股",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month_str",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
