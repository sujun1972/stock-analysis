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
from .daily_basic_repository import DailyBasicRepository
from .hk_hold_repository import HkHoldRepository
from .stk_limit_repository import StkLimitRepository
from .block_trade_repository import BlockTradeRepository
from .concept_repository import ConceptRepository

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
    # 扩展数据
    "DailyBasicRepository",
    "HkHoldRepository",
    "StkLimitRepository",
    "BlockTradeRepository",
    # 概念板块
    "ConceptRepository",
]
