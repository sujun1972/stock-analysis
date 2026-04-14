"""
最强板块统计 Service
"""
import asyncio
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from app.repositories import LimitCptRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class LimitCptService:
    """最强板块统计业务逻辑层"""

    def __init__(self):
        self.limit_cpt_repo = LimitCptRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.calendar_repo = TradingCalendarRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ LimitCptService initialized")

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：今天有数据则返回今天，否则返回最近有数据的交易日（YYYY-MM-DD格式）
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(
            self.limit_cpt_repo.exists_by_date, today
        )
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"

        latest = await asyncio.to_thread(
            self.limit_cpt_repo.get_latest_trade_date
        )
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_limit_cpt_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = 'asc'
    ) -> Dict:
        """
        获取最强板块统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码
            limit: 每页记录数
            offset: 偏移量（分页）
            sort_by: 排序字段
            sort_order: 排序方向

        Returns:
            数据字典，包含 items、total、statistics
        """
        # 并发获取数据、总数和统计
        items_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_by_date_range,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        total_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_count_by_date_range,
            start_date=start_date,
            end_date=end_date,
            ts_code=ts_code
        )
        statistics_coro = asyncio.to_thread(
            self.limit_cpt_repo.get_statistics,
            start_date=start_date,
            end_date=end_date
        )

        items, total, statistics = await asyncio.gather(
            items_coro, total_coro, statistics_coro
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return {
            "items": items,
            "total": total,
            "statistics": statistics
        }

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取最强板块统计信息

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD

        Returns:
            统计信息字典
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 获取统计信息
        statistics = await asyncio.to_thread(
            self.limit_cpt_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        return statistics

    async def get_latest_data(self) -> Dict:
        """
        获取最新交易日的最强板块统计数据

        Returns:
            最新数据字典
        """
        # 获取最新交易日期
        latest_date = await asyncio.to_thread(
            self.limit_cpt_repo.get_latest_trade_date
        )

        if not latest_date:
            return {"items": [], "total": 0}

        # 获取该日期的数据
        items = await asyncio.to_thread(
            self.limit_cpt_repo.get_by_trade_date,
            trade_date=latest_date
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return {
            "items": items,
            "total": len(items),
            "latest_date": self._format_date(latest_date)
        }

    async def get_top_by_up_nums(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取涨停家数排名TOP数据

        Args:
            trade_date: 交易日期，格式：YYYY-MM-DD
            limit: 返回记录数

        Returns:
            排名TOP数据列表
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        trade_date_fmt = trade_date.replace('-', '') if trade_date else None

        # 获取TOP数据
        items = await asyncio.to_thread(
            self.limit_cpt_repo.get_top_by_up_nums,
            trade_date=trade_date_fmt,
            limit=limit
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        return items

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'limit_cpt')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'limit_cpt', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步（标准入口，逐交易日同步并记录 sync_history）"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        trading_days = await asyncio.to_thread(
            self.calendar_repo.get_trading_days_between, start_date, end_date
        )

        logger.info(f"[limit_cpt] 增量同步 {len(trading_days)} 个交易日 ({start_date}~{end_date})")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'limit_cpt', 'incremental', 'by_date', start_date,
        )
        try:
            total_records = 0
            for trade_date in trading_days:
                try:
                    result = await self.sync_limit_cpt(trade_date=trade_date)
                    total_records += result.get('records', 0)
                except Exception as e:
                    logger.error(f"[limit_cpt] {trade_date} 同步失败: {e}")

            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', total_records, end_date, None,
            )
            return {"status": "success", "records": total_records}
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    async def sync_limit_cpt(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步最强板块统计数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 板块代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步最强板块统计数据: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 从 Tushare 获取数据（分页，单次上限 2000 条）
            MAX_OFFSET = 100_000
            PAGE_SIZE = 2000
            provider = self._get_provider()
            all_frames = []
            offset = 0
            while True:
                if offset >= MAX_OFFSET:
                    logger.warning(f"[limit_cpt] offset 已达 {MAX_OFFSET} 上限，停止分页")
                    break
                df = await asyncio.to_thread(
                    provider.get_limit_cpt_list,
                    trade_date=trade_date,
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    limit=PAGE_SIZE,
                    offset=offset
                )
                if df is None or df.empty:
                    break
                all_frames.append(df)
                if len(df) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE

            if not all_frames:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据（可能是非交易日或数据尚未更新）"
                }

            df = pd.concat(all_frames, ignore_index=True)
            logger.info(f"从 Tushare 获取到 {len(df)} 条记录")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.limit_cpt_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条最强板块统计数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步最强板块统计数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> list:
        """将日期范围切分为自然月片段，每片返回 (month_start, month_end)，均为 YYYYMMDD。"""
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
        """按自然月切片全量同步最强板块统计历史数据（支持 Redis 续继）

        Redis Key: sync:limit_cpt:full_history:progress
        """
        FULL_HISTORY_START_DATE = "20100101"
        PROGRESS_KEY = "sync:limit_cpt:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量limit_cpt] 共 {total} 个月度片段")

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
                    MAX_OFFSET = 100_000
                    PAGE_SIZE = 2000
                    all_frames = []
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(f"[全量limit_cpt] {ms}-{me} offset 达上限，停止分页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_limit_cpt_list,
                            start_date=ms,
                            end_date=me,
                            limit=PAGE_SIZE,
                            offset=offset
                        )
                        if df is None or df.empty:
                            break
                        all_frames.append(df)
                        if len(df) < PAGE_SIZE:
                            break
                        offset += PAGE_SIZE
                    records = 0
                    if all_frames:
                        df = pd.concat(all_frames, ignore_index=True)
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.limit_cpt_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量limit_cpt] 片段 {ms}-{me} 失败: {e}")
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = concurrency * 2
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[sync_month(ms, me) for ms, me in batch])

            for ms, _me, ok, records, _err in results:
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
                        'current': done, 'total': total, 'percent': pct,
                        'success': success_count, 'skipped': skip_count,
                        'errors': error_count, 'records': total_records
                    }
                )

        all_done = (skip_count + success_count) >= total
        if all_done and error_count == 0:
            redis_client.delete(PROGRESS_KEY)
            logger.info(f"[全量limit_cpt] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count, 'skipped': skip_count,
            'errors': error_count, 'records': total_records,
            'total_segments': total
        }

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 确保必要字段存在
        required_columns = ['trade_date', 'ts_code', 'name', 'rank']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")

        # 移除空记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 确保数值类型正确
        numeric_columns = ['days', 'cons_nums', 'up_nums', 'pct_chg', 'rank']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据验证和清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: 日期字符串（YYYYMMDD）

        Returns:
            格式化后的日期（YYYY-MM-DD）
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
