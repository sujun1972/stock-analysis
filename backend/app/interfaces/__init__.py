"""
服务接口定义

提供基于 Protocol 和 ABC 的服务契约定义，
确保类型安全和明确的服务边界。
"""

from .backtest_interfaces import (
    IBacktestDataLoader,
    IBacktestExecutor,
    IBacktestResultFormatter,
    IBacktestService,
)
from .config_interfaces import IConfigService, IDataSourceManager, ISyncStatusManager
from .experiment_interfaces import IBatchManager, IExperimentRunner, IExperimentService
from .ml_interfaces import IMLTrainingService, IModelPredictor, ITrainingTaskManager
from .sync_interfaces import (
    IDailySyncService,
    IRealtimeSyncService,
    IStockListSyncService,
    ISyncService,
)

__all__ = [
    # Sync interfaces
    "ISyncService",
    "IStockListSyncService",
    "IDailySyncService",
    "IRealtimeSyncService",
    # ML interfaces
    "IMLTrainingService",
    "IModelPredictor",
    "ITrainingTaskManager",
    # Backtest interfaces
    "IBacktestService",
    "IBacktestDataLoader",
    "IBacktestExecutor",
    "IBacktestResultFormatter",
    # Experiment interfaces
    "IExperimentService",
    "IBatchManager",
    "IExperimentRunner",
    # Config interfaces
    "IConfigService",
    "IDataSourceManager",
    "ISyncStatusManager",
]
