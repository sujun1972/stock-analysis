"""
公司公告同步服务（AkShare 东方财富聚合）

三条入口：
  - sync_incremental(start_date?, end_date?)：逐交易日调 AkShare 全市场公告并入库；
    默认回看 `sync_configs.incremental_default_days` 天（最少 1 天）。
  - sync_by_stock(ts_code, days=90)：被动同步单只股票，调 AkShare 个股公告接口。
  - sync_full_history(redis_client, start_date?, concurrency=5, update_state_fn=None)：
    按交易日并发拉全市场公告，Redis Set 续继（key: sync:stock_anns:full_history:progress）。

数据源策略：与 limit_list_d 对齐（逐交易日 + 月维度全量），但改走 AkShareProvider。
Service 不继承 TushareSyncBase（接口签名不兼容），手写流程并手动记录 sync_history。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from app.repositories.stock_anns_repository import StockAnnsRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository


class StockAnnsSyncService:
    """公司公告同步服务。"""

    TABLE_KEY = "stock_anns"
    FULL_HISTORY_START_DATE = "20200101"  # 东方财富公告聚合最早覆盖日期（经验值）
    FULL_HISTORY_PROGRESS_KEY = "sync:stock_anns:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:stock_anns:full_history:lock"

    def __init__(self) -> None:
        self.anns_repo = StockAnnsRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.sync_config_repo = SyncConfigRepository()
        self.calendar_repo = TradingCalendarRepository()

    # -------------------------------------------------
    # Provider（惰性初始化，fork worker 友好）
    # -------------------------------------------------

    def _get_provider(self):
        cached = getattr(self, '_provider', None)
        if cached is not None:
            return cached
        from core.src.providers import DataProviderFactory
        self._provider = DataProviderFactory.create_provider(source='akshare')
        return self._provider

    # -------------------------------------------------
    # 增量（逐交易日拉全市场公告）
    # -------------------------------------------------

    async def get_suggested_start_date(self) -> str:
        """候选起始 = min(今天 - incremental_default_days, 上次成功的 data_end_date)。"""
        cfg = await asyncio.to_thread(self.sync_config_repo.get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=int(default_days))).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,  # 占位，兼容 Celery 工厂签名；始终 by_date
        max_requests_per_minute: Optional[int] = None,  # AkShare 无速率参数，接收并忽略
    ) -> Dict[str, Any]:
        """标准增量入口（无参数时从 sync_configs 自动计算起始日期）。

        - 按 `TradingCalendarRepository.get_trading_days_between` 展开交易日列表
        - 每个交易日调 `AkShareProvider.get_market_anns(date)` → `bulk_upsert`
        - 全程手动记录 sync_history（避免依赖 TushareSyncBase）
        """
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        trading_days: List[str] = await asyncio.to_thread(
            self.calendar_repo.get_trading_days_between, start_date, end_date
        )
        if not trading_days:
            logger.info(f"[stock_anns] 增量同步无交易日 ({start_date}~{end_date})")
            return {"status": "success", "records": 0, "trading_days": 0}

        logger.info(f"[stock_anns] 增量同步 {len(trading_days)} 个交易日 ({start_date}~{end_date})")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, self.TABLE_KEY, 'incremental', 'by_date', start_date,
        )
        total_records = 0
        errors: List[str] = []
        last_success_date: Optional[str] = None
        try:
            for trade_date in trading_days:
                try:
                    records = await self._sync_one_market_day(trade_date)
                    total_records += records
                    last_success_date = trade_date
                except Exception as e:
                    err = f"{trade_date}: {e}"
                    errors.append(err)
                    logger.warning(f"[stock_anns] 交易日 {trade_date} 同步失败: {e}")
                    # 失败不中断，继续下一个交易日

            status = 'success' if not errors else ('success' if total_records > 0 else 'failure')
            err_msg = '; '.join(errors[:3]) if errors else None
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, status, total_records, last_success_date or end_date, err_msg,
            )
            return {
                "status": status,
                "records": total_records,
                "trading_days": len(trading_days),
                "errors": errors,
            }
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', total_records, last_success_date, str(e),
            )
            raise

    async def _sync_one_market_day(self, trade_date: str) -> int:
        """单个交易日：拉全市场公告并 upsert，返回入库条数。"""
        provider = self._get_provider()
        response = await asyncio.to_thread(provider.get_market_anns, trade_date)
        if not response.is_success() and response.status.name != 'WARNING':
            raise RuntimeError(
                f"AkShare get_market_anns {trade_date} 失败: {response.error or response.error_code}"
            )
        df = response.data
        if df is None or df.empty:
            logger.debug(f"[stock_anns] {trade_date} 无公告")
            return 0
        count = await asyncio.to_thread(self.anns_repo.bulk_upsert, df)
        logger.info(f"[stock_anns] {trade_date} 入库 {count} 条（共 {len(df)} 条）")
        return count

    # -------------------------------------------------
    # 被动同步（单只股票）
    # -------------------------------------------------

    async def sync_by_stock(
        self,
        ts_code: str,
        days: int = 90,
    ) -> Dict[str, Any]:
        """被动同步单只股票近 `days` 天的公告。

        调用 `ak.stock_individual_notice_report`，比全市场接口快很多（单次 1~3s），
        适合前端打开个股 AI 分析前的静默刷新。
        """
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=int(days))).strftime('%Y%m%d')

        provider = self._get_provider()
        response = await asyncio.to_thread(
            provider.get_stock_anns, ts_code, start_date, end_date
        )
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

        count = await asyncio.to_thread(self.anns_repo.bulk_upsert, df)
        logger.info(f"[stock_anns] 被动同步 {ts_code} 入库 {count} 条（近 {days} 天）")
        return {"status": "success", "records": count, "ts_code": ts_code, "days": int(days)}

    # -------------------------------------------------
    # 全量历史（按交易日并发 + Redis Set 续继）
    # -------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        update_state_fn=None,
        max_requests_per_minute: int = 0,  # AkShare 接口本身限速，不再额外节流
    ) -> Dict[str, Any]:
        """按交易日并发全量拉取公告，Redis Set 记录已完成交易日，中断可续继。

        注意：AkShare 全市场接口单日耗时 60~120s。**每天 ~5000 条 × 1500 个交易日 ≈ 750 万行**。
        可通过前端 `sync_configs.full_history_start_date` 缩短覆盖窗口以控制耗时（如只拉近半年）。
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime('%Y%m%d')

        trading_days: List[str] = await asyncio.to_thread(
            self.calendar_repo.get_trading_days_between, effective_start, today
        )
        total = len(trading_days)
        if total == 0:
            return {"status": "success", "success": 0, "skipped": 0, "errors": 0, "records": 0}

        logger.info(f"[全量 stock_anns] 起始={effective_start} 今日={today} 共 {total} 个交易日")

        # 读续继进度
        completed = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY) if redis_client else set()
        completed = {d.decode() if isinstance(d, bytes) else d for d in (completed or set())}
        pending = [d for d in trading_days if d not in completed]
        skip_count = len(completed)
        success_count = 0
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(max(1, concurrency))

        async def _sync_one(trade_date: str):
            async with sem:
                try:
                    records = await self._sync_one_market_day(trade_date)
                    return trade_date, True, records, None
                except Exception as e:
                    logger.warning(f"[全量 stock_anns] {trade_date} 失败: {e}")
                    return trade_date, False, 0, str(e)

        BATCH_SIZE = max(1, concurrency) * 2
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[_sync_one(d) for d in batch])
            for trade_date, ok, records, _ in results:
                if ok:
                    if redis_client:
                        redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, trade_date)
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

        all_done = (skip_count + success_count) >= total
        if all_done and error_count == 0 and redis_client:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info(f"[全量 stock_anns] 全部完成，已清除进度记录")

        return {
            "status": "success",
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "total_trading_days": total,
        }

    # -------------------------------------------------
    # 查询辅助（API 层薄包装）
    # -------------------------------------------------

    async def resolve_default_ann_date(self) -> Optional[str]:
        """前端未传日期时返回最近有数据的 ann_date（YYYY-MM-DD）。"""
        latest = await asyncio.to_thread(self.anns_repo.get_latest_ann_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def list_anns(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        anno_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> Dict[str, Any]:
        """分页查询（前端公告浏览页用）。"""
        items, total, anno_types = await asyncio.gather(
            asyncio.to_thread(
                self.anns_repo.query_by_filters,
                ts_code=ts_code, start_date=start_date, end_date=end_date,
                anno_type=anno_type, keyword=keyword,
                page=page, page_size=page_size,
                sort_by=sort_by, sort_order=sort_order,
            ),
            asyncio.to_thread(
                self.anns_repo.count_by_filters,
                ts_code=ts_code, start_date=start_date, end_date=end_date,
                anno_type=anno_type, keyword=keyword,
            ),
            asyncio.to_thread(self.anns_repo.get_distinct_anno_types, 90, 200),
        )
        return {
            'items': items,
            'total': total,
            'anno_types': anno_types,
            'page': int(page),
            'page_size': int(page_size),
        }

    async def get_recent_by_stock(self, ts_code: str, days: int = 30, limit: int = 50) -> List[Dict]:
        """CIO Tool / 个股专家使用：最近 N 天的公告列表。"""
        return await asyncio.to_thread(self.anns_repo.query_by_stock, ts_code, int(days), int(limit))
