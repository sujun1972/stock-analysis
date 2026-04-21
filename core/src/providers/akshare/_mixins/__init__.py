"""
AkShareProvider Mixin 模块

按功能域拆分 AkShareProvider 的方法：
- NewsAndAnnsMixin:       新闻资讯 & 公司公告（替代 Tushare anns_d / news / cctv_news）
- MacroIndicatorsMixin:   宏观经济指标（替代 Tushare 宏观日历，CPI/PPI/PMI/M2/新增社融/GDP/Shibor）

历史方法（股票列表、行情、分时、实时行情）目前仍内联在 `provider.py`，后续可视需要拆分。
"""

from .news_and_anns import NewsAndAnnsMixin
from .macro_indicators import MacroIndicatorsMixin

__all__ = [
    'NewsAndAnnsMixin',
    'MacroIndicatorsMixin',
]
