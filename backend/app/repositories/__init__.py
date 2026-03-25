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
from .sentiment_ai_analysis_repository import SentimentAiAnalysisRepository
from .stock_daily_repository import StockDailyRepository
from .user_quota_repository import UserQuotaRepository
from .stock_basic_repository import StockBasicRepository
from .task_execution_history_repository import TaskExecutionHistoryRepository
from .top_list_repository import TopListRepository
from .top_inst_repository import TopInstRepository
from .limit_list_repository import LimitListRepository
from .limit_step_repository import LimitStepRepository
from .limit_cpt_repository import LimitCptRepository
from .report_rc_repository import ReportRcRepository
from .stk_shock_repository import StkShockRepository
from .stk_alert_repository import StkAlertRepository
from .stk_high_shock_repository import StkHighShockRepository
from .pledge_stat_repository import PledgeStatRepository
from .repurchase_repository import RepurchaseRepository
from .share_float_repository import ShareFloatRepository
from .stk_holdernumber_repository import StkHolderNumberRepository
from .stk_holdertrade_repository import StkHoldertradeRepository
from .income_repository import IncomeRepository
from .balancesheet_repository import BalancesheetRepository
from .cashflow_repository import CashflowRepository
from .forecast_repository import ForecastRepository
from .express_repository import ExpressRepository
from .dividend_repository import DividendRepository
from .fina_indicator_repository import FinaIndicatorRepository
from .fina_audit_repository import FinaAuditRepository
from .fina_mainbz_repository import FinaMainbzRepository
from .disclosure_date_repository import DisclosureDateRepository
from .cyq_perf_repository import CyqPerfRepository
from .cyq_chips_repository import CyqChipsRepository
from .ccass_hold_repository import CcassHoldRepository
from .ccass_hold_detail_repository import CcassHoldDetailRepository
from .stk_auction_o_repository import StkAuctionORepository
from .stk_auction_c_repository import StkAuctionCRepository
from .stk_nineturn_repository import StkNineturnRepository
from .stk_ah_comparison_repository import StkAhComparisonRepository
from .stk_surv_repository import StkSurvRepository
from .broker_recommend_repository import BrokerRecommendRepository
from .suspend_repository import SuspendRepository
from .stk_limit_d_repository import StkLimitDRepository
from .hsgt_top10_repository import HsgtTop10Repository
from .ggt_top10_repository import GgtTop10Repository
from .ggt_daily_repository import GgtDailyRepository
from .ggt_monthly_repository import GgtMonthlyRepository
from .stock_realtime_repository import StockRealtimeRepository
from .stock_st_repository import StockStRepository

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
    "HsgtTop10Repository",
    "GgtTop10Repository",
    "GgtDailyRepository",
    "GgtMonthlyRepository",
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
    "StkLimitDRepository",
    "BlockTradeRepository",
    "SuspendRepository",
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
    "SentimentAiAnalysisRepository",
    # 股票数据
    "StockDailyRepository",
    "StockBasicRepository",
    "StockRealtimeRepository",
    "StockStRepository",
    # 用户管理
    "UserQuotaRepository",
    # 打板专题
    "TopListRepository",
    "TopInstRepository",
    "LimitListRepository",
    "LimitStepRepository",
    "LimitCptRepository",
    # 特色数据
    "ReportRcRepository",
    "CyqPerfRepository",
    "CyqChipsRepository",
    "CcassHoldRepository",
    "CcassHoldDetailRepository",
    "StkAuctionORepository",
    "StkAuctionCRepository",
    "StkNineturnRepository",
    "StkAhComparisonRepository",
    "StkSurvRepository",
    "BrokerRecommendRepository",
    # 参考数据
    "StkShockRepository",
    "StkAlertRepository",
    "StkHighShockRepository",
    "PledgeStatRepository",
    "RepurchaseRepository",
    "ShareFloatRepository",
    "StkHolderNumberRepository",
    "StkHoldertradeRepository",
    # 财务数据
    "IncomeRepository",
    "BalancesheetRepository",
    "CashflowRepository",
    "ForecastRepository",
    "ExpressRepository",
    "DividendRepository",
    "FinaIndicatorRepository",
    "FinaAuditRepository",
    "FinaMainbzRepository",
    "DisclosureDateRepository",
]
