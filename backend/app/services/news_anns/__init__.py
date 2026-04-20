"""
新闻资讯 & 公司公告服务包。

子模块：
  - retry_decorator              Service 层通用指数退避装饰器（AkShare 爬虫共用）
  - stock_anns_sync_service      公司公告同步（全市场 + 被动单股 + 全量历史）
  - anns_content_fetcher         公告全文按需抓取（HTML/PDF）

数据源策略：AkShare 优先，轻量爬虫次选；完全避免 Tushare 付费接口（anns_d 等）。
"""

from app.services.news_anns.retry_decorator import (
    AkShareRateLimitError,
    AkShareRetryDecorator,
    AkShareRetryExhaustedError,
)
from app.services.news_anns.stock_anns_sync_service import StockAnnsSyncService

__all__ = [
    'AkShareRetryDecorator',
    'AkShareRateLimitError',
    'AkShareRetryExhaustedError',
    'StockAnnsSyncService',
]
