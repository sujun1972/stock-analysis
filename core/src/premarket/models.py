"""
盘前预期管理数据模型

定义盘前数据的结构化表示。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime


@dataclass
class OvernightData:
    """隔夜外盘数据"""
    trade_date: str

    # A50期指
    a50_close: float = 0.0
    a50_change: float = 0.0
    a50_amplitude: float = 0.0

    # 中概股指数
    china_concept_close: float = 0.0
    china_concept_change: float = 0.0

    # 大宗商品
    wti_crude_close: float = 0.0
    wti_crude_change: float = 0.0
    comex_gold_close: float = 0.0
    comex_gold_change: float = 0.0
    lme_copper_close: float = 0.0
    lme_copper_change: float = 0.0

    # 外汇
    usdcnh_close: float = 0.0
    usdcnh_change: float = 0.0

    # 美股三大指数
    sp500_close: float = 0.0
    sp500_change: float = 0.0
    nasdaq_close: float = 0.0
    nasdaq_change: float = 0.0
    dow_close: float = 0.0
    dow_change: float = 0.0

    fetch_time: Optional[datetime] = None


@dataclass
class PremarketNews:
    """盘前核心新闻"""
    news_time: str
    source: str  # 'cailianshe', 'jin10'
    title: str
    content: str
    keywords: List[str] = field(default_factory=list)
    importance_level: str = 'medium'  # 'critical', 'high', 'medium'
    affects_holdings: bool = False
    related_stocks: List[Dict] = field(default_factory=list)


@dataclass
class MacroTone:
    """宏观定调"""
    direction: str  # '高开', '低开', '平开'
    confidence: str  # 置信度
    a50_impact: str  # A50的具体影响
    reasoning: str  # 推理过程


@dataclass
class HoldingsAlert:
    """持仓排雷"""
    has_risk: bool
    affected_sectors: List[str] = field(default_factory=list)
    affected_stocks: List[Dict] = field(default_factory=list)
    actions: str = ''


@dataclass
class PlanAdjustment:
    """计划修正"""
    cancel_buy: List[Dict] = field(default_factory=list)
    early_stop_loss: List[Dict] = field(default_factory=list)
    keep_plan: str = ''
    reasoning: str = ''


@dataclass
class AuctionFocus:
    """竞价盯盘"""
    stocks: List[Dict] = field(default_factory=list)
    conditions: Dict[str, str] = field(default_factory=dict)
    actions: str = ''


@dataclass
class CollisionAnalysisResult:
    """碰撞分析结果"""
    trade_date: str

    # 四个维度
    macro_tone: Optional[MacroTone] = None
    holdings_alert: Optional[HoldingsAlert] = None
    plan_adjustment: Optional[PlanAdjustment] = None
    auction_focus: Optional[AuctionFocus] = None

    # 核心指令
    action_command: str = ''

    # 元数据
    ai_provider: str = ''
    ai_model: str = ''
    tokens_used: int = 0
    generation_time: float = 0.0
    status: str = 'pending'

    # 输入数据
    yesterday_tactics_summary: Dict[str, Any] = field(default_factory=dict)
    overnight_summary: Dict[str, Any] = field(default_factory=dict)
    critical_news_summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PremarketSyncResult:
    """盘前数据同步结果"""
    success: bool
    trade_date: str
    is_trading_day: bool
    synced_tables: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
