"""
大盘资金流向业务逻辑层（东方财富DC）

提供大盘主力资金流向数据业务逻辑处理，包含数据查询、统计分析等功能。
数据源：东方财富大盘资金流向
"""

import asyncio
import calendar
from datetime import datetime, date
from typing import Dict, Optional
from loguru import logger

from app.repositories.moneyflow_mkt_dc_repository import MoneyflowMktDcRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class MoneyflowMktDcService:
    """大盘资金流向业务逻辑层"""

    def __init__(self):
        self.repo = MoneyflowMktDcRepository()
        logger.debug("✓ MoneyflowMktDcService initialized")

    def get_moneyflow_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """获取大盘资金流向数据（带分页和统计）"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            limit=limit,
            offset=offset
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 单位换算：元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100000000, 2)

        for key in ['avg_net', 'max_net', 'min_net', 'total_net', 'avg_elg', 'max_elg', 'avg_lg', 'max_lg']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 100000000, 2)

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    def get_latest_moneyflow(self) -> Optional[Dict]:
        """获取最新的大盘资金流向数据"""
        data = self.repo.get_latest()

        if not data:
            return None

        # 单位换算：元 -> 亿元
        for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
            if key in data and data[key]:
                data[key] = round(data[key] / 100000000, 2)

        return data

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = DataProviderFactory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> list:
        """将日期范围切分为自然月片段，每片返回 (month_start, month_end)，均为 YYYYMMDD。

        大盘DC每天只有一条记录（一个大盘），每月约 20 条，按月切片远低于 5000 上限。
        """
        start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        cur = date(start_d.year, start_d.month, 1)
        while cur <= end_d:
            ms = max(cur, start_d)
            last_day = calendar.monthrange(cur.year, cur.month)[1]
            me = min(date(cur.year, cur.month, last_day), end_d)
            segments.append((ms.strftime('%Y%m%d'), me.strftime('%Y%m%d')))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)
        return segments

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        update_state_fn=None
    ) -> Dict:
        """按自然月切片全量同步大盘资金流向历史数据（支持 Redis 续继）

        大盘DC每天一条记录，每月约 20 条，单次请求远低于 5000 上限，直接按月切片即可。

        Redis Key: sync:moneyflow_mkt_dc:full_history:progress
        Redis 续继 Key 格式："{month_start}"（每月起始日期）
        """
        FULL_HISTORY_START_DATE = "20150101"
        PROGRESS_KEY = "sync:moneyflow_mkt_dc:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量moneyflow_mkt_dc] 共 {total} 个月度片段")

        completed_set = redis_client.smembers(PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [(ms, me) for ms, me in all_segments if ms not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider()
        sem = asyncio.Semaphore(max(1, concurrency))

        async def sync_month(ms: str, me: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_moneyflow_mkt_dc,
                        start_date=ms,
                        end_date=me
                    )
                    records = 0
                    if df is not None and not df.empty:
                        records = await asyncio.to_thread(self.repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量moneyflow_mkt_dc] 片段 {ms}-{me} 失败: {e}")
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = concurrency * 2
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[sync_month(ms, me) for ms, me in batch])

            for ms, me, ok, records, err in results:
                if ok:
                    redis_client.sadd(PROGRESS_KEY, ms)
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
                        'current': done,
                        'total': total,
                        'percent': pct,
                        'success': success_count,
                        'skipped': skip_count,
                        'errors': error_count,
                        'records': total_records
                    }
                )

        all_done = (skip_count + success_count) >= total
        if all_done and error_count == 0:
            redis_client.delete(PROGRESS_KEY)
            logger.info(f"[全量moneyflow_mkt_dc] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count,
            'skipped': skip_count,
            'errors': error_count,
            'records': total_records,
            'total_segments': total
        }
