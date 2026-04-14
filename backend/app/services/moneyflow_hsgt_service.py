"""
沪深港通资金流向业务逻辑层

提供沪股通、深股通、港股通的资金流向数据业务逻辑处理，
包含数据查询、统计分析等功能。

数据源：Tushare沪深港通资金流向
"""

import asyncio
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from loguru import logger

from app.repositories.moneyflow_hsgt_repository import MoneyflowHsgtRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class MoneyflowHsgtService:
    """
    沪深港通资金流向业务逻辑层

    职责：
    - 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    - 数据聚合和统计
    - 最新数据查询
    - 分页处理
    """

    def __init__(self):
        """初始化Service，注入Repository依赖"""
        self.repo = MoneyflowHsgtRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ MoneyflowHsgtService initialized")

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'moneyflow_hsgt')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'moneyflow_hsgt', 'incremental'
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

        logger.info(f"[moneyflow_hsgt] 增量同步 start_date={start_date} end_date={end_date}")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'moneyflow_hsgt', 'incremental', sync_strategy or 'by_date_range', start_date,
        )
        try:
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_moneyflow_hsgt,
                start_date=start_date,
                end_date=end_date
            )
            records = 0
            if df is not None and not df.empty:
                records = await asyncio.to_thread(self.repo.bulk_upsert, df)
            result = {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条沪深港通资金流向数据"
            }
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', records, end_date, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    def get_moneyflow_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取沪深港通资金流向数据（带分页和统计）

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数
            offset: 偏移量

        Returns:
            包含数据列表、统计信息和总数的字典

        Examples:
            >>> service = MoneyflowHsgtService()
            >>> result = service.get_moneyflow_data(start_date='2024-01-01')
        """
        # 1. 日期格式转换（业务逻辑）
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 2. 获取数据（通过 Repository）
        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            limit=limit,
            offset=offset
        )

        # 3. 获取总数（通过 Repository）
        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 4. 获取统计信息（通过 Repository）
        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 5. 单位换算：百万元 -> 亿元（业务逻辑）
        for item in items:
            for key in ['ggt_ss', 'ggt_sz', 'hgt', 'sgt', 'north_money', 'south_money']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100, 2)

        for key in ['avg_north', 'max_north', 'min_north', 'total_north',
                    'avg_south', 'max_south', 'min_south', 'total_south']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 100, 2)

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    def get_latest_moneyflow(self) -> Optional[Dict]:
        """
        获取最新的资金流向数据

        Returns:
            最新资金流向数据，如果没有数据则返回None

        Examples:
            >>> service = MoneyflowHsgtService()
            >>> latest = service.get_latest_moneyflow()
        """
        # 获取最新数据（通过 Repository）
        data = self.repo.get_latest()

        if not data:
            return None

        # 单位换算：百万元 -> 亿元（业务逻辑）
        for key in ['ggt_ss', 'ggt_sz', 'hgt', 'sgt', 'north_money', 'south_money']:
            if key in data and data[key]:
                data[key] = round(data[key] / 100, 2)

        # 计算净流入（业务逻辑）
        if data.get('north_money') is not None and data.get('south_money') is not None:
            data['net_inflow'] = round(data['north_money'] - data['south_money'], 2)
        else:
            data['net_inflow'] = 0

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

        hsgt 每天4条记录（沪股通/深股通/港股通沪/港股通深），每月约 80 条，
        按月切片远低于 5000 上限。
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
        """按自然月切片全量同步沪深港通资金流向历史数据（支持 Redis 续继）

        Redis Key: sync:moneyflow_hsgt:full_history:progress
        Redis 续继 Key 格式："{month_start}"（每月起始日期）
        """
        FULL_HISTORY_START_DATE = "20140101"
        PROGRESS_KEY = "sync:moneyflow_hsgt:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量moneyflow_hsgt] 共 {total} 个月度片段")

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
                        provider.get_moneyflow_hsgt,
                        start_date=ms,
                        end_date=me
                    )
                    records = 0
                    if df is not None and not df.empty:
                        records = await asyncio.to_thread(self.repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量moneyflow_hsgt] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量moneyflow_hsgt] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count,
            'skipped': skip_count,
            'errors': error_count,
            'records': total_records,
            'total_segments': total
        }
