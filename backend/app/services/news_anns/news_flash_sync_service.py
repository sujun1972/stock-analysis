"""
财经快讯同步服务（AkShare 财新 + 东财个股新闻）

两条入口：
  - sync_incremental():              拉取财新要闻精选最近 ~100 条（当前时刻），写入 news_flash
  - sync_by_stock(ts_code, days=7):  被动同步单只股票的东财个股新闻（近 ~10 条）

不做全量历史：AkShare 这两个接口都不支持日期参数，每次返回"最近若干条"；
历史快讯只能靠日常增量积累。

统一在 Service 层：
  - StockCodeExtractor 把 title/summary 正则匹配到的代码 + stock_basic 白名单过滤后，
    写回 related_ts_codes（eastmoney 已自带 ts_code，caixin 需抽取）
  - 手动维护 sync_history（避免依赖 TushareSyncBase）
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
from loguru import logger

from app.repositories.news_flash_repository import NewsFlashRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.news_anns.stock_code_extractor import StockCodeExtractor


class NewsFlashSyncService:
    """财经快讯同步服务。"""

    TABLE_KEY = "news_flash"
    # 快讯无历史接口，全量同步实际等价于增量（仅为了兼容同步配置页"全量"按钮）
    FULL_HISTORY_PROGRESS_KEY = "sync:news_flash:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:news_flash:full_history:lock"

    def __init__(self) -> None:
        self.repo = NewsFlashRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.sync_config_repo = SyncConfigRepository()

    # -------------------------------------------------
    # Provider（惰性初始化）
    # -------------------------------------------------

    def _get_provider(self):
        cached = getattr(self, '_provider', None)
        if cached is not None:
            return cached
        from core.src.providers import DataProviderFactory
        self._provider = DataProviderFactory.create_provider(source='akshare')
        return self._provider

    # -------------------------------------------------
    # 增量：财新快讯（无日期参数，始终拉最近 ~100 条）
    # -------------------------------------------------

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,  # 占位兼容 Celery 工厂签名
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """拉取财新要闻精选最近 ~100 条，去重写入 news_flash。

        接口无日期参数，每次拉全量"最近"。高频调用（如每 5 分钟一次）可持续积累历史。
        """
        today = datetime.now().strftime('%Y%m%d')
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, self.TABLE_KEY, 'incremental', 'latest', today,
        )
        try:
            records = await self._sync_caixin_once()
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', records, today, None,
            )
            return {"status": "success", "records": records, "source": "caixin"}
        except Exception as e:
            logger.error(f"[news_flash] 增量同步失败: {e}")
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    async def _sync_caixin_once(self) -> int:
        """拉取财新要闻精选并入库（Service 内部调用）。"""
        provider = self._get_provider()
        response = await asyncio.to_thread(provider.get_news_flash, 'caixin')
        if not response.is_success() and response.status.name != 'WARNING':
            raise RuntimeError(
                f"AkShare get_news_flash(caixin) 失败: {response.error or response.error_code}"
            )
        df = response.data
        if df is None or df.empty:
            return 0
        # caixin 无关联股，需从 title/summary 正则 + stock_basic 白名单抽取 related_ts_codes
        items = df.to_dict(orient='records')
        StockCodeExtractor.extract_from_items(items)
        df2 = pd.DataFrame(items, columns=df.columns)
        count = await asyncio.to_thread(self.repo.bulk_upsert, df2)
        logger.info(f"[news_flash] caixin 入库 {count} 条（输入 {len(df2)}）")
        return count

    # -------------------------------------------------
    # 被动同步（单只股票，东财个股新闻）
    # -------------------------------------------------

    async def sync_by_stock(
        self,
        ts_code: str,
        days: int = 7,  # 占位：东财接口不支持天数参数，保留以兼容 Celery 被动同步签名
    ) -> Dict[str, Any]:
        """被动同步单只股票近 ~10 条个股新闻。

        数据源：`ak.stock_news_em`，无日期参数；本方法每次拉接口返回的最新 ~10 条。
        """
        provider = self._get_provider()
        response = await asyncio.to_thread(provider.get_stock_news, ts_code)
        if not response.is_success() and response.status.name != 'WARNING':
            return {
                "status": "error",
                "records": 0,
                "error": response.error or response.error_code,
                "ts_code": ts_code,
            }
        df = response.data
        if df is None or df.empty:
            return {"status": "success", "records": 0, "ts_code": ts_code}

        # eastmoney 来源天然带 [ts_code]；这里再跑一遍抽取是为了合并文本里提到的其他关联股
        items = df.to_dict(orient='records')
        StockCodeExtractor.extract_from_items(items)
        df2 = pd.DataFrame(items, columns=df.columns)
        count = await asyncio.to_thread(self.repo.bulk_upsert, df2)
        logger.info(f"[news_flash] 被动同步 {ts_code} 入库 {count} 条")
        return {"status": "success", "records": count, "ts_code": ts_code}

    # -------------------------------------------------
    # 全量历史（兼容同步配置页按钮；本数据源无真正的历史）
    # -------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 1,
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict[str, Any]:
        """AkShare 快讯接口无历史参数，所谓"全量"等价于一次增量抓取。"""
        logger.info("[news_flash] 快讯接口不支持历史回溯，退化为单次增量抓取")
        records = await self._sync_caixin_once()
        return {
            "status": "success",
            "success": 1 if records > 0 else 0,
            "skipped": 0,
            "errors": 0,
            "records": records,
            "note": "AkShare caixin/eastmoney 快讯接口不支持按日期回溯，仅能靠日常增量积累",
        }

    # -------------------------------------------------
    # 查询辅助
    # -------------------------------------------------

    async def list_flash(
        self,
        source: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        ts_code: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> Dict[str, Any]:
        items, total, sources = await asyncio.gather(
            asyncio.to_thread(
                self.repo.query_by_filters,
                source=source, start_time=start_time, end_time=end_time,
                ts_code=ts_code, keyword=keyword, tag=tag,
                page=page, page_size=page_size,
                sort_by=sort_by, sort_order=sort_order,
            ),
            asyncio.to_thread(
                self.repo.count_by_filters,
                source=source, start_time=start_time, end_time=end_time,
                ts_code=ts_code, keyword=keyword, tag=tag,
            ),
            asyncio.to_thread(self.repo.get_distinct_sources),
        )
        return {
            'items': items,
            'total': total,
            'sources': sources,
            'page': int(page),
            'page_size': int(page_size),
        }

    async def get_recent_by_stock(self, ts_code: str, days: int = 7, limit: int = 50):
        """CIO Tool / 个股专家使用：该股最近 N 天快讯。"""
        return await asyncio.to_thread(self.repo.query_by_stock, ts_code, int(days), int(limit))
