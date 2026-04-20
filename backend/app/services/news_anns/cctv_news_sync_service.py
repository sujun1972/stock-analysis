"""
新闻联播同步服务（AkShare `news_cctv`）

三条入口：
  - sync_incremental(start_date?, end_date?): 按"自然日"逐日拉取并入库，默认回看
    `sync_configs.incremental_default_days` 天
  - sync_by_date(date): 指定日期单次同步（API/CIO 调用入口）
  - sync_full_history(redis_client, start_date?, concurrency=1, ...): 按日并发全量
    （该接口单日 3-8s，不建议高并发；Redis Set 记录已完成日期续继）

与公告/快讯不同：新闻联播按"自然日"而非"交易日"统计（节假日放假除外，接口会返回空）。
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from app.repositories.cctv_news_repository import CctvNewsRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository


class CctvNewsSyncService:
    """新闻联播同步服务。"""

    TABLE_KEY = "cctv_news"
    FULL_HISTORY_START_DATE = "20200101"  # AkShare 覆盖 2016-02 起，本项目限近 5 年内
    FULL_HISTORY_PROGRESS_KEY = "sync:cctv_news:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:cctv_news:full_history:lock"

    def __init__(self) -> None:
        self.repo = CctvNewsRepository()
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
    # 增量
    # -------------------------------------------------

    async def get_suggested_start_date(self) -> str:
        cfg = await asyncio.to_thread(self.sync_config_repo.get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 3) if cfg else 3
        candidate = (datetime.now() - timedelta(days=int(default_days))).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按自然日逐日拉取新闻联播。默认回看 sync_configs.incremental_default_days 天。"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        days = self._generate_days(start_date, end_date)
        if not days:
            logger.info(f"[cctv_news] 增量无日期 ({start_date}~{end_date})")
            return {"status": "success", "records": 0, "days": 0}

        logger.info(f"[cctv_news] 增量 {len(days)} 天 ({start_date}~{end_date})")
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, self.TABLE_KEY, 'incremental', 'by_date', start_date,
        )
        total_records = 0
        errors: List[str] = []
        last_success: Optional[str] = None
        try:
            for d in days:
                try:
                    records = await self._sync_one_day(d)
                    total_records += records
                    if records > 0:
                        last_success = d
                except Exception as e:
                    errors.append(f"{d}: {e}")
                    logger.warning(f"[cctv_news] {d} 同步失败: {e}")
            status = 'success' if not errors else ('success' if total_records > 0 else 'failure')
            err_msg = '; '.join(errors[:3]) if errors else None
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, status, total_records, last_success or end_date, err_msg,
            )
            return {
                "status": status, "records": total_records, "days": len(days), "errors": errors,
            }
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', total_records, last_success, str(e),
            )
            raise

    async def _sync_one_day(self, news_date: str) -> int:
        """拉取单日新闻联播并 upsert，返回条数。"""
        provider = self._get_provider()
        response = await asyncio.to_thread(provider.get_cctv_news, news_date)
        if not response.is_success() and response.status.name != 'WARNING':
            raise RuntimeError(
                f"AkShare get_cctv_news({news_date}) 失败: {response.error or response.error_code}"
            )
        df = response.data
        if df is None or df.empty:
            logger.debug(f"[cctv_news] {news_date} 无联播（可能放假/停播）")
            return 0
        count = await asyncio.to_thread(self.repo.bulk_upsert, df)
        logger.info(f"[cctv_news] {news_date} 入库 {count} 条（原始 {len(df)}）")
        return count

    # -------------------------------------------------
    # 指定单日同步（API 用）
    # -------------------------------------------------

    async def sync_by_date(self, news_date: str) -> Dict[str, Any]:
        records = await self._sync_one_day(news_date)
        return {"status": "success", "records": records, "news_date": news_date}

    # -------------------------------------------------
    # 全量历史（按日并发 + Redis Set 续继）
    # -------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 1,
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict[str, Any]:
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime('%Y%m%d')
        days = self._generate_days(effective_start, today)
        total = len(days)
        if total == 0:
            return {"status": "success", "success": 0, "skipped": 0, "errors": 0, "records": 0}

        logger.info(f"[全量 cctv_news] 起始={effective_start} 今日={today} 共 {total} 天")

        completed = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY) if redis_client else set()
        completed = {d.decode() if isinstance(d, bytes) else d for d in (completed or set())}
        pending = [d for d in days if d not in completed]

        skip_count = len(completed)
        success_count = 0
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(max(1, concurrency))

        async def _sync_one(d: str):
            async with sem:
                try:
                    records = await self._sync_one_day(d)
                    return d, True, records, None
                except Exception as e:
                    logger.warning(f"[全量 cctv_news] {d} 失败: {e}")
                    return d, False, 0, str(e)

        BATCH_SIZE = max(1, concurrency) * 4
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[_sync_one(d) for d in batch])
            for d, ok, records, _ in results:
                if ok:
                    if redis_client:
                        redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, d)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
            if update_state_fn:
                done = skip_count + success_count + error_count
                pct = int(done / total * 100) if total > 0 else 0
                update_state_fn(
                    state='PROGRESS',
                    meta={
                        'current': done, 'total': total, 'percent': pct,
                        'success': success_count, 'skipped': skip_count,
                        'errors': error_count, 'records': total_records,
                    },
                )

        if (skip_count + success_count) >= total and error_count == 0 and redis_client:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量 cctv_news] 全部完成，已清除进度记录")

        return {
            "status": "success",
            "success": success_count, "skipped": skip_count, "errors": error_count,
            "records": total_records, "total_days": total,
        }

    # -------------------------------------------------
    # 查询辅助
    # -------------------------------------------------

    async def list_news(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> Dict[str, Any]:
        items, total, dates = await asyncio.gather(
            asyncio.to_thread(
                self.repo.query_by_filters,
                start_date=start_date, end_date=end_date, keyword=keyword,
                page=page, page_size=page_size,
                sort_by=sort_by, sort_order=sort_order,
            ),
            asyncio.to_thread(
                self.repo.count_by_filters,
                start_date=start_date, end_date=end_date, keyword=keyword,
            ),
            asyncio.to_thread(self.repo.get_distinct_dates, 60),
        )
        return {
            'items': items, 'total': total, 'dates': dates,
            'page': int(page), 'page_size': int(page_size),
        }

    async def get_recent(self, days: int = 3, limit: int = 60):
        """CIO Tool / 宏观专家使用：最近 N 天联播汇总。"""
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=int(days))).strftime('%Y%m%d')
        return await asyncio.to_thread(
            self.repo.query_by_filters,
            start_date=start, end_date=end,
            page=1, page_size=int(limit),
            sort_by='news_date', sort_order='desc',
        )

    # -------------------------------------------------
    # 内部工具
    # -------------------------------------------------

    @staticmethod
    def _generate_days(start: str, end: str) -> List[str]:
        """YYYYMMDD 范围 → 逐日 YYYYMMDD 列表（含首尾）。"""
        s = date(int(start[:4]), int(start[4:6]), int(start[6:8]))
        e = date(int(end[:4]), int(end[4:6]), int(end[6:8]))
        if s > e:
            return []
        days = []
        cur = s
        while cur <= e:
            days.append(cur.strftime('%Y%m%d'))
            cur += timedelta(days=1)
        return days
