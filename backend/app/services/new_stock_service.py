"""
新股列表服务（new_stocks 表）

对应 Tushare new_share 接口，存储完整 IPO 数据：
发行量、发行价、市盈率、募集资金、中签率等。

接口限制：单次最大 2000 条，A 股每季度新股约 100-200 只，
全量同步时按 CHUNK_DAYS 天切片，不会触及上限。
"""

import asyncio
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from app.repositories.new_stocks_repository import NewStocksRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings

# 全量同步时每次请求覆盖的天数（约1季度，远低于2000条上限）
CHUNK_DAYS = 90
# 并发请求数（new_share 接口无需太多并发，避免触发限流）
CONCURRENCY = 5


class NewStockService:
    """新股列表服务"""

    def __init__(self):
        self.repo = NewStocksRepository()

    def _get_provider(self):
        return DataProviderFactory.create_provider('tushare', token=settings.TUSHARE_TOKEN)

    # ── 查询 ──────────────────────────────────────────────────

    async def get_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        items, total = await asyncio.gather(
            asyncio.to_thread(self.repo.get_by_date_range, start_date, end_date, limit, offset),
            asyncio.to_thread(self.repo.count_by_date_range, start_date, end_date),
        )
        return {"items": items, "total": total}

    async def get_statistics(self) -> Dict:
        return await asyncio.to_thread(self.repo.get_statistics)

    # ── 同步 ──────────────────────────────────────────────────

    async def sync_new_stocks(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 90,
    ) -> Dict:
        """
        从 Tushare new_share 接口同步数据到 new_stocks 表。

        - 增量同步（不传 start_date）：按 days 天范围一次性拉取
        - 全量同步（传入 start_date）：按 CHUNK_DAYS 天切片，CONCURRENCY 并发
        """
        try:
            ed = end_date or datetime.now().strftime('%Y%m%d')

            if start_date:
                # 全量/范围同步：切片并发
                total_records = await self._sync_chunked(start_date, ed)
            else:
                # 增量同步：一次性拉取最近 days 天
                sd = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
                total_records = await self._fetch_and_save(sd, ed)

            logger.info(f"new_stocks 同步完成：共写入 {total_records} 条")
            return {"status": "success", "records": total_records}

        except Exception as e:
            logger.error(f"new_stocks 同步失败: {e}")
            raise

    # ── 内部 ──────────────────────────────────────────────────

    async def _sync_chunked(self, start_date: str, end_date: str) -> int:
        """按 CHUNK_DAYS 切片、CONCURRENCY 并发拉取并写库。"""
        chunks = self._build_date_chunks(start_date, end_date, CHUNK_DAYS)
        logger.info(f"全量同步 new_stocks：{len(chunks)} 个切片（{start_date}~{end_date}，每片 {CHUNK_DAYS} 天）")

        semaphore = asyncio.Semaphore(CONCURRENCY)
        total_records = 0

        async def fetch_chunk(sd: str, ed: str) -> int:
            async with semaphore:
                return await self._fetch_and_save(sd, ed)

        for batch_start in range(0, len(chunks), CONCURRENCY):
            batch = chunks[batch_start:batch_start + CONCURRENCY]
            results = await asyncio.gather(
                *[fetch_chunk(s, e) for s, e in batch],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.error(f"切片同步出错: {r}")
                else:
                    total_records += r
            done = min(batch_start + CONCURRENCY, len(chunks))
            logger.info(f"进度：{done}/{len(chunks)} 个切片，已写入 {total_records} 条")

        return total_records

    async def _fetch_and_save(self, start_date: str, end_date: str) -> int:
        """拉取单个切片数据并写库，返回写入条数。"""
        provider = self._get_provider()
        response = await asyncio.to_thread(
            provider.get_new_stocks,
            90,           # days 参数（start_date 优先，此值不生效）
            start_date,
            end_date,
        )
        if not response or not response.is_success():
            logger.warning(f"切片 {start_date}~{end_date} 接口调用失败")
            return 0

        df = response.data
        if df is None or df.empty:
            return 0

        count = await asyncio.to_thread(self.repo.bulk_upsert, df)
        return count

    @staticmethod
    def _build_date_chunks(
        start_date: str, end_date: str, chunk_days: int
    ) -> List[Tuple[str, str]]:
        """将 [start_date, end_date] 按 chunk_days 切成片段列表。"""
        fmt = '%Y%m%d'
        cur = datetime.strptime(start_date, fmt)
        end = datetime.strptime(end_date, fmt)
        chunks = []
        while cur <= end:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
            chunks.append((cur.strftime(fmt), chunk_end.strftime(fmt)))
            cur = chunk_end + timedelta(days=1)
        return chunks

