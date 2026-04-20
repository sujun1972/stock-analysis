"""
AkShareProvider Mixin 模块

按功能域拆分 AkShareProvider 的方法：
- NewsAndAnnsMixin:  新闻资讯 & 公司公告（AkShare 免费接口，替代 Tushare 付费的 anns_d / news / cctv_news 等）

历史方法（股票列表、行情、分时、实时行情）目前仍内联在 `provider.py`，后续可视需要拆分。
"""

from .news_and_anns import NewsAndAnnsMixin

__all__ = [
    'NewsAndAnnsMixin',
]
