"""
TushareProvider Mixin 模块

将 TushareProvider 的方法按功能域拆分为独立 Mixin：
- StockListMixin:    股票列表（get_stock_list, get_new_stocks, get_delisted_stocks）
- MarketDataMixin:   行情数据（get_daily_data, get_daily_batch, get_minute_data, get_realtime_quotes）
- ExtendedDataMixin: 扩展基础数据（get_daily_basic, get_moneyflow, get_adj_factor, get_margin 等）
- FundFlowMixin:     资金流向/交易监控（get_moneyflow_hsgt, get_limit_list_d, get_stk_alert 等）
- CorporateMixin:    公司行为/财务报表（get_income, get_balancesheet, get_dividend, get_forecast 等）
- AdvancedMixin:     高级特色数据（get_cyq_perf, get_dc_index, get_ggt_daily, get_trade_calendar 等）
"""

from .stock_list import StockListMixin
from .market_data import MarketDataMixin
from .extended_data import ExtendedDataMixin
from .fund_flow import FundFlowMixin
from .corporate import CorporateMixin
from .advanced import AdvancedMixin

__all__ = [
    'StockListMixin',
    'MarketDataMixin',
    'ExtendedDataMixin',
    'FundFlowMixin',
    'CorporateMixin',
    'AdvancedMixin',
]
