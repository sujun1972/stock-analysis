"""板块资金流向业务逻辑层（东财概念及行业板块资金流向 DC）"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.moneyflow_ind_dc_repository import MoneyflowIndDcRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class MoneyflowIndDcService:
    """板块资金流向业务逻辑层"""

    FULL_HISTORY_START_DATE = "20150101"
    FULL_HISTORY_PROGRESS_KEY = "sync:moneyflow_ind_dc:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:moneyflow_ind_dc:full_history:lock"
    # 板块类型：行业、概念、地域。全量同步需逐类型拉取
    CONTENT_TYPES = ["行业", "概念", "地域"]

    def __init__(self):
        self.repo = MoneyflowIndDcRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ MoneyflowIndDcService initialized")

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'moneyflow_ind_dc')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'moneyflow_ind_dc', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步（标准入口，自动计算日期范围并记录 sync_history）"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"[moneyflow_ind_dc] 增量同步 start_date={start_date} end_date={end_date}")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'moneyflow_ind_dc', 'incremental', sync_strategy or 'by_date_range', start_date,
        )
        try:
            provider = self._get_provider()
            total_records = 0
            for ct in self.CONTENT_TYPES:
                df = await asyncio.to_thread(
                    provider.get_moneyflow_ind_dc,
                    start_date=start_date,
                    end_date=end_date,
                    content_type=ct
                )
                if df is not None and not df.empty:
                    records = await asyncio.to_thread(self.repo.bulk_upsert, df)
                    total_records += records
            result = {
                "status": "success",
                "records": total_records,
                "message": f"成功同步 {total_records} 条板块资金流向数据"
            }
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', total_records, end_date, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    @staticmethod
    def _generate_weeks(start_date: str, end_date: str, window: int = 7) -> list:
        """将日期范围切分为固定天数窗口，每片返回 (window_start, window_end)，均为 YYYYMMDD。

        window=7 时约每月产生 4~5 片。行业（~100板块/天）每片 ~700 条，
        地域（~20板块/天）每片 ~140 条，均安全低于 5000 条上限。
        概念（~1500板块/天）每片 ~10500 条仍超限，因此概念类型改用按天切片（window=1）。
        实际调用时按 content_type 自动选择窗口大小。
        """
        from datetime import timedelta
        start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        cur = start_d
        while cur <= end_d:
            ms = cur
            me = min(cur + timedelta(days=window - 1), end_d)
            segments.append((ms.strftime('%Y%m%d'), me.strftime('%Y%m%d')))
            cur = me + timedelta(days=1)
        return segments

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        update_state_fn=None
    ) -> Dict:
        """按日期窗口切片 × 三板块类型，全量同步板块资金流向历史数据（支持 Redis 续继）

        切片策略（单次上限 5000 条）：
          - 行业（~100板块）：7天窗口，每片约 700 条 ✓
          - 地域（~20板块）：7天窗口，每片约 140 条 ✓
          - 概念（~1500板块）：1天窗口，每片约 1500 条 ✓

        Redis Key: sync:moneyflow_ind_dc:full_history:progress
        Redis 续继 Key 格式："{window_start}:{content_type}"
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        # 行业/地域用7天窗口，概念用1天窗口
        WINDOW_MAP = {"行业": 7, "地域": 7, "概念": 1}

        all_segments = []
        for ct in self.CONTENT_TYPES:
            window = WINDOW_MAP[ct]
            for ms, me in self._generate_weeks(effective_start, today, window=window):
                all_segments.append((ms, me, ct))

        total = len(all_segments)
        logger.info(
            f"[全量moneyflow_ind_dc] 共 {total} 个片段 "
            f"（行业/地域 7天窗口，概念 1天窗口）"
        )

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        # Redis Key 格式："{ms}:{content_type}"
        pending = [(ms, me, ct) for ms, me, ct in all_segments if f"{ms}:{ct}" not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider()
        sem = asyncio.Semaphore(max(1, concurrency))

        async def sync_segment(ms: str, me: str, ct: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_moneyflow_ind_dc,
                        start_date=ms,
                        end_date=me,
                        content_type=ct
                    )
                    records = 0
                    if df is not None and not df.empty:
                        records = await asyncio.to_thread(self.repo.bulk_upsert, df)
                    return ms, me, ct, True, records, None
                except Exception as e:
                    return ms, me, ct, False, 0, str(e)

        BATCH_SIZE = max(1, concurrency) * 2
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_segment(ms, me, ct) for ms, me, ct in batch])
            for ms, me, ct, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, f"{ms}:{ct}")
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量moneyflow_ind_dc] {ms}~{me} {ct} 失败（下次续继）: {err}")

            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(
                    state='PROGRESS',
                    meta={
                        'current': done,
                        'total': total,
                        'percent': round(done / total * 100, 1),
                        'records': total_records,
                        'errors': error_count
                    }
                )
            logger.info(
                f"[全量moneyflow_ind_dc] 进度: {done}/{total} ({round(done / total * 100, 1)}%) "
                f"入库={total_records} 失败={error_count}"
            )

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量moneyflow_ind_dc] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": f"同步完成 {success_count} 个片段，入库 {total_records} 条，失败 {error_count} 个"
        }

    # 原始数据单位为元，统一换算为亿元
    _AMOUNT_KEYS = ('net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount')
    _STATS_AMOUNT_KEYS = (
        'avg_net_amount', 'max_net_amount', 'min_net_amount', 'total_net_amount',
        'avg_buy_elg_amount', 'max_buy_elg_amount', 'avg_buy_lg_amount', 'max_buy_lg_amount',
    )

    def _convert_items_to_yi(self, items: List[Dict]) -> None:
        """将 items 中的金额字段从元原地换算为亿元（就地修改）"""
        for item in items:
            for key in self._AMOUNT_KEYS:
                if item.get(key) is not None:
                    item[key] = round(item[key] / 100_000_000, 2)

    def _convert_stats_to_yi(self, statistics: Dict) -> None:
        """将统计字典中的金额字段从元原地换算为亿元（就地修改）"""
        for key in self._STATS_AMOUNT_KEYS:
            if statistics.get(key) is not None:
                statistics[key] = round(statistics[key] / 100_000_000, 2)

    async def resolve_default_trade_date(self, content_type: Optional[str] = None) -> Optional[str]:
        """返回最近有数据的交易日（YYYY-MM-DD），供前端回填日期选择器"""
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.repo.get_latest_trade_date, content_type)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    def get_moneyflow_data(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        # 保留旧参数兼容性
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict:
        """获取板块资金流向数据

        Note: trade_date 优先于 start_date/end_date；ts_code 参数保留用于 API 兼容性，目前未使用
        """
        # trade_date 优先
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
            start_date_fmt = trade_date_fmt
            end_date_fmt = trade_date_fmt
        else:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

        # 分页：兼容旧 limit/offset，新接口用 page/page_size
        if limit is not None:
            actual_limit = limit
            actual_offset = offset
        else:
            actual_limit = page_size
            actual_offset = (page - 1) * page_size

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            content_type=content_type,
            limit=actual_limit,
            offset=actual_offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type
        )

        self._convert_items_to_yi(items)
        self._convert_stats_to_yi(statistics)

        # 解析实际查询日期，供前端回填（trade_date 单日模式时直接返回）
        resolved_trade_date = None
        if trade_date:
            resolved_trade_date = trade_date if '-' in trade_date else \
                f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
        elif items:
            raw = items[0].get('trade_date', '')
            if raw and len(raw) == 8:
                resolved_trade_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": actual_limit,
            "offset": actual_offset,
            "trade_date": resolved_trade_date,
        }

    def get_latest_moneyflow(self, content_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """获取最新交易日的板块资金流向数据"""
        items = self.repo.get_latest(content_type=content_type, limit=limit)
        self._convert_items_to_yi(items)
        return items
