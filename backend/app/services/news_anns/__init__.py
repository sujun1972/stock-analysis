"""
新闻资讯 & 公司公告服务包。

子模块：
  - retry_decorator              Service 层通用指数退避装饰器（AkShare 爬虫共用）
  - stock_anns_sync_service      公司公告同步（Phase 1：全市场 + 被动单股 + 全量历史）
  - anns_content_fetcher         公告全文按需抓取（HTML/PDF）
  - news_flash_sync_service      财经快讯同步（Phase 2：财新要闻 + 东财个股新闻）
  - cctv_news_sync_service       新闻联播同步（Phase 2：按自然日 + 全量续继）
  - stock_code_extractor         快讯正文个股代码抽取（正则 + stock_basic 白名单）

数据源策略：AkShare 优先，轻量爬虫次选；完全避免 Tushare 付费接口（anns_d / news / cctv_news 等）。
"""

from app.services.news_anns.retry_decorator import (
    AkShareRateLimitError,
    AkShareRetryDecorator,
    AkShareRetryExhaustedError,
)
from app.services.news_anns.stock_anns_sync_service import StockAnnsSyncService
from app.services.news_anns.news_flash_sync_service import NewsFlashSyncService
from app.services.news_anns.cctv_news_sync_service import CctvNewsSyncService
from app.services.news_anns.stock_code_extractor import StockCodeExtractor

__all__ = [
    'AkShareRetryDecorator',
    'AkShareRateLimitError',
    'AkShareRetryExhaustedError',
    'StockAnnsSyncService',
    'NewsFlashSyncService',
    'CctvNewsSyncService',
    'StockCodeExtractor',
]
