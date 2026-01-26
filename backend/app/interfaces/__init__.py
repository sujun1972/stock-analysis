"""
服务接口定义

提供基于 Protocol 和 ABC 的服务契约定义，
确保类型安全和明确的服务边界。
"""

from .sync_interfaces import (
    ISyncService,
    IStockListSyncService,
    IDailySyncService,
    IRealtimeSyncService
)

from .ml_interfaces import (
    IMLTrainingService,
    IModelPredictor,
    ITrainingTaskManager
)

from .backtest_interfaces import (
    IBacktestService,
    IBacktestDataLoader,
    IBacktestExecutor,
    IBacktestResultFormatter
)

from .experiment_interfaces import (
    IExperimentService,
    IBatchManager,
    IExperimentRunner
)

from .config_interfaces import (
    IConfigService,
    IDataSourceManager,
    ISyncStatusManager
)

__all__ = [
    # Sync interfaces
    'ISyncService',
    'IStockListSyncService',
    'IDailySyncService',
    'IRealtimeSyncService',

    # ML interfaces
    'IMLTrainingService',
    'IModelPredictor',
    'ITrainingTaskManager',

    # Backtest interfaces
    'IBacktestService',
    'IBacktestDataLoader',
    'IBacktestExecutor',
    'IBacktestResultFormatter',

    # Experiment interfaces
    'IExperimentService',
    'IBatchManager',
    'IExperimentRunner',

    # Config interfaces
    'IConfigService',
    'IDataSourceManager',
    'ISyncStatusManager',
]
