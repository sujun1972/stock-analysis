"""
市场情绪数据模型

定义市场情绪相关的数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date, datetime


@dataclass
class TradingCalendar:
    """交易日历"""
    trade_date: str
    is_trading_day: bool
    exchange: str = 'SSE'
    day_type: Optional[str] = None  # '工作日', '周末', '节假日'
    holiday_name: Optional[str] = None


@dataclass
class MarketIndices:
    """大盘指数数据"""
    trade_date: str

    # 上证指数
    sh_index_code: str = '000001'
    sh_index_close: float = 0.0
    sh_index_change: float = 0.0
    sh_index_amplitude: float = 0.0
    sh_index_volume: int = 0
    sh_index_amount: float = 0.0

    # 深成指数
    sz_index_code: str = '399001'
    sz_index_close: float = 0.0
    sz_index_change: float = 0.0
    sz_index_amplitude: float = 0.0
    sz_index_volume: int = 0
    sz_index_amount: float = 0.0

    # 创业板指数
    cyb_index_code: str = '399006'
    cyb_index_close: float = 0.0
    cyb_index_change: float = 0.0
    cyb_index_amplitude: float = 0.0
    cyb_index_volume: int = 0
    cyb_index_amount: float = 0.0

    # 市场汇总
    total_volume: int = 0
    total_amount: float = 0.0


@dataclass
class LimitUpStock:
    """涨停股票信息"""
    code: str
    name: str
    days: int  # 连板天数
    reason: str = ''  # 涨停原因
    first_limit_time: str = ''  # 首次涨停时间
    last_limit_time: str = ''  # 最后涨停时间


@dataclass
class BlastStock:
    """炸板股票信息"""
    code: str
    name: str
    blast_times: int  # 炸板次数
    final_change: float = 0.0  # 最终涨跌幅


@dataclass
class LimitUpPool:
    """涨停板情绪池"""
    trade_date: str

    # 涨跌停统计
    limit_up_count: int = 0
    limit_down_count: int = 0

    # 炸板数据
    blast_count: int = 0
    blast_rate: float = 0.0

    # 连板数据
    max_continuous_days: int = 0
    max_continuous_count: int = 0
    continuous_ladder: Dict[str, int] = field(default_factory=dict)

    # 股票列表
    limit_up_stocks: List[Dict] = field(default_factory=list)
    blast_stocks: List[Dict] = field(default_factory=list)

    # 市场统计
    total_stocks: int = 0
    rise_count: int = 0
    fall_count: int = 0
    rise_fall_ratio: float = 0.0


@dataclass
class Seat:
    """龙虎榜席位"""
    rank: int
    name: str
    amount: float


@dataclass
class DragonTigerRecord:
    """龙虎榜记录"""
    trade_date: str
    stock_code: str
    stock_name: str

    # 上榜原因
    reason: str
    reason_type: str = ''

    # 股票行情
    close_price: float = 0.0
    price_change: float = 0.0
    turnover_rate: float = 0.0

    # 买卖数据
    buy_amount: float = 0.0
    sell_amount: float = 0.0
    net_amount: float = 0.0

    # 席位信息
    top_buyers: List[Dict] = field(default_factory=list)
    top_sellers: List[Dict] = field(default_factory=list)

    # 机构信息
    has_institution: bool = False
    institution_count: int = 0

    # 营业部统计
    dept_buy_count: int = 0
    dept_sell_count: int = 0


@dataclass
class SentimentSyncResult:
    """情绪数据同步结果"""
    success: bool
    is_trading_day: bool
    synced_tables: List[str] = field(default_factory=list)
    error: Optional[str] = None
    details: Dict = field(default_factory=dict)


# ==================== 情绪周期相关模型 ====================

@dataclass
class SentimentCycle:
    """市场情绪周期数据"""
    trade_date: str

    # 情绪周期阶段
    cycle_stage: str  # 'freezing', 'starting', 'fermenting', 'retreating'
    cycle_stage_cn: str  # '冰点', '启动', '发酵', '退潮'
    confidence_score: float = 0.0  # 置信度 0-100

    # 计算指标
    limit_up_count: int = 0
    limit_down_count: int = 0
    limit_ratio: float = 0.0
    blast_count: int = 0
    blast_rate: float = 0.0
    max_continuous_days: int = 0
    max_continuous_count: int = 0
    continuous_growth_rate: float = 0.0

    # 核心指数
    money_making_index: float = 0.0  # 赚钱效应指数 0-100
    sentiment_score: float = 0.0  # 综合情绪得分 0-100

    # 阶段统计
    stage_duration_days: int = 1
    previous_stage: Optional[str] = None
    stage_change_date: Optional[str] = None

    # 市场统计
    total_stocks: int = 0
    rise_count: int = 0
    fall_count: int = 0
    rise_fall_ratio: float = 0.0
    total_amount: float = 0.0
    amount_change_rate: float = 0.0

    # 详细分析
    analysis_result: Dict = field(default_factory=dict)


@dataclass
class HotMoneySeat:
    """游资席位信息"""
    seat_name: str
    seat_type: str  # 'top_tier', 'famous', 'retail_base', 'institution', 'unknown'
    seat_label: str  # '[一线顶级游资]', '[知名游资]', '[散户大本营]', '[机构]'

    # 匹配规则
    match_keywords: List[str] = field(default_factory=list)
    match_type: str = 'exact'
    priority: int = 0

    # 席位信息
    city: Optional[str] = None
    broker: Optional[str] = None
    branch_office: Optional[str] = None
    region: Optional[str] = None

    # 统计信息
    appearance_count: int = 0
    total_buy_amount: float = 0.0
    total_sell_amount: float = 0.0
    net_amount: float = 0.0
    win_rate: Optional[float] = None
    avg_hold_days: Optional[float] = None

    # 席位特征
    trade_style: Optional[str] = None
    specialty_sectors: List[str] = field(default_factory=list)
    is_active: bool = True
    activity_level: str = 'medium'

    # 标签
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None

    # 数据更新
    last_appearance_date: Optional[str] = None
    data_source: str = 'manual'


@dataclass
class HotMoneyOperation:
    """游资操作记录"""
    trade_date: str
    seat_id: Optional[int] = None
    seat_name: str = ''
    seat_type: str = ''
    seat_label: str = ''

    # 股票信息
    stock_code: str = ''
    stock_name: str = ''

    # 交易数据
    operation_type: str = 'buy'  # 'buy', 'sell', 'both'
    buy_amount: float = 0.0
    sell_amount: float = 0.0
    net_amount: float = 0.0
    buy_rank: Optional[int] = None
    sell_rank: Optional[int] = None

    # 股票行情
    close_price: float = 0.0
    price_change: float = 0.0
    is_limit_up: bool = False
    continuous_days: int = 0

    # 统计分析
    is_leading_stock: bool = False
    sector: Optional[str] = None


@dataclass
class DragonTigerAnalysis:
    """龙虎榜深度分析结果"""
    trade_date: str

    # 机构分析
    institution_top_stocks: List[Dict] = field(default_factory=list)
    institution_total_buy: float = 0.0
    institution_total_sell: float = 0.0
    institution_net_buy: float = 0.0
    institution_stock_count: int = 0

    # 顶级游资分析
    top_tier_hot_money_stocks: List[Dict] = field(default_factory=list)
    top_tier_total_buy: float = 0.0
    top_tier_appearance_count: int = 0

    # 散户大本营分析
    retail_base_stocks: List[Dict] = field(default_factory=list)
    retail_base_total_buy: float = 0.0

    # 游资活跃度
    hot_money_activity: Dict = field(default_factory=dict)

    # 市场特征
    market_characteristics: Dict = field(default_factory=dict)


@dataclass
class CycleCalculationResult:
    """情绪周期计算结果"""
    trade_date: str
    cycle_data: SentimentCycle
    calculation_details: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
