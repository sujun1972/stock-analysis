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
