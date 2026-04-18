"""大宗交易同步任务（工厂生成）"""

from app.tasks._task_factory import make_full_history_task, make_incremental_task

sync_block_trade_task = make_incremental_task(
    name="tasks.sync_block_trade",
    service_path="app.services.block_trade_service:BlockTradeService",
    display_name="大宗交易",
    raw_sync_method="sync_block_trade",
    raw_param_names=("trade_date", "ts_code", "start_date", "end_date"),
    incremental_extra_kwargs=("sync_strategy", "max_requests_per_minute"),
)

sync_block_trade_full_history_task = make_full_history_task(
    name="tasks.sync_block_trade_full_history",
    service_path="app.services.block_trade_service:BlockTradeService",
    table_key="block_trade",
    display_name="大宗交易",
    soft_time_limit=7200,
    time_limit=10800,
    default_strategy="by_month",
    accept_strategy_param=True,
    accept_max_rpm=True,
)
