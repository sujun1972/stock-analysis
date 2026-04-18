"""ST股票列表同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_stock_st_incremental_task = make_incremental_task(
    name="tasks.sync_stock_st_incremental",
    service_path="app.services.stock_st_service:StockStService",
    display_name="ST股票列表",
    raw_sync_method="sync_incremental",  # 无 raw 路径，永远走 sync_incremental
    raw_param_names=(),
    incremental_extra_kwargs=("start_date", "end_date", "sync_strategy", "max_requests_per_minute"),
    max_retries=2,
    retry_backoff=180,
    retry_jitter=True,
)

sync_stock_st_full_history_task = make_full_history_task(
    name="tasks.sync_stock_st_full_history",
    service_path="app.services.stock_st_service:StockStService",
    table_key="stock_st",
    display_name="ST股票列表",
    default_concurrency=1,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
