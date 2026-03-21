"""Repository layer for data access"""

from .base_repository import BaseRepository
from .batch_repository import BatchRepository
from .experiment_repository import ExperimentRepository
from .strategy_config_repository import StrategyConfigRepository
from .dynamic_strategy_repository import DynamicStrategyRepository
from .strategy_execution_repository import StrategyExecutionRepository
from .strategy_repository import StrategyRepository  # Phase 2: 统一策略
from .moneyflow_repository import MoneyflowRepository
from .moneyflow_hsgt_repository import MoneyflowHsgtRepository
from .moneyflow_mkt_dc_repository import MoneyflowMktDcRepository
from .moneyflow_ind_dc_repository import MoneyflowIndDcRepository
from .moneyflow_stock_dc_repository import MoneyflowStockDcRepository
from .margin_repository import MarginRepository
from .margin_detail_repository import MarginDetailRepository
from .margin_secs_repository import MarginSecsRepository
from .slb_len_repository import SlbLenRepository
from .daily_basic_repository import DailyBasicRepository
from .hk_hold_repository import HkHoldRepository
from .stk_limit_repository import StkLimitRepository
from .block_trade_repository import BlockTradeRepository
from .concept_repository import ConceptRepository
from .sync_log_repository import SyncLogRepository
from .config_repository import ConfigRepository
from .celery_task_history_repository import CeleryTaskHistoryRepository
from .scheduled_task_repository import ScheduledTaskRepository
from .trading_calendar_repository import TradingCalendarRepository
from .market_sentiment_repository import MarketSentimentRepository
from .limit_up_pool_repository import LimitUpPoolRepository
from .dragon_tiger_list_repository import DragonTigerListRepository
from .sentiment_cycle_repository import SentimentCycleRepository
from .sentiment_ai_analysis_repository import SentimentAiAnalysisRepository
from .stock_daily_repository import StockDailyRepository
from .user_quota_repository import UserQuotaRepository
from .stock_basic_repository import StockBasicRepository
from .task_execution_history_repository import TaskExecutionHistoryRepository
from .top_list_repository import TopListRepository

__all__ = [
    "BaseRepository",
    "ExperimentRepository",
    "BatchRepository",
    # Phase 2: 统一策略
    "StrategyRepository",
    # 旧架构 (将逐步废弃)
    "StrategyConfigRepository",
    "DynamicStrategyRepository",
    "StrategyExecutionRepository",
    # 资金流向 - Tushare标准
    "MoneyflowRepository",
    # 资金流向 - 沪深港通
    "MoneyflowHsgtRepository",
    # 资金流向 - 东方财富DC
    "MoneyflowMktDcRepository",
    "MoneyflowIndDcRepository",
    "MoneyflowStockDcRepository",
    # 融资融券
    "MarginRepository",
    "MarginDetailRepository",
    "MarginSecsRepository",
    # 转融通
    "SlbLenRepository",
    # 扩展数据
    "DailyBasicRepository",
    "HkHoldRepository",
    "StkLimitRepository",
    "BlockTradeRepository",
    # 概念板块
    "ConceptRepository",
    # 配置和同步
    "ConfigRepository",
    "SyncLogRepository",
    # 任务管理
    "CeleryTaskHistoryRepository",
    "ScheduledTaskRepository",
    "TaskExecutionHistoryRepository",
    # 交易日历
    "TradingCalendarRepository",
    # 市场情绪
    "MarketSentimentRepository",
    "LimitUpPoolRepository",
    "DragonTigerListRepository",
    "SentimentCycleRepository",
    "SentimentAiAnalysisRepository",
    # 股票数据
    "StockDailyRepository",
    "StockBasicRepository",
    # 用户管理
    "UserQuotaRepository",
    # 打板专题
    "TopListRepository",
]
