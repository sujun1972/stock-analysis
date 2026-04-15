"""
融资融券标的 Service

业务逻辑层，处理融资融券标的数据的同步、查询和统计
"""

import asyncio
import calendar
from typing import Dict, Optional
from datetime import datetime, date, timedelta
from loguru import logger
import pandas as pd

from app.repositories import MarginSecsRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase


class MarginSecsService(TushareSyncBase):
    """融资融券标的服务"""

    TABLE_KEY = 'margin_secs'

    def __init__(self):
        """初始化服务"""
        super().__init__()
        self.margin_secs_repo = MarginSecsRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ MarginSecsService initialized")

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'margin_secs')
        default_days = (cfg.get('incremental_default_days') or 1) if cfg else 1
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'margin_secs', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(self, start_date=None, end_date=None, sync_strategy=None, max_requests_per_minute=None) -> Dict:
        """增量同步（通过基类 run_incremental_sync 实现自动切片+翻页）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        if start_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)
        # margin_secs 没有 provider 封装方法，直接用 pro API
        fetch_fn = provider.api_client.pro.margin_secs

        return await self.run_incremental_sync(
            fetch_fn=fetch_fn,
            upsert_fn=self.margin_secs_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
        )

    async def sync_margin_secs(
        self,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步融资融券标的数据

        Args:
            trade_date: 交易日期（YYYYMMDD）
            exchange: 交易所代码（SSE/SZSE/BSE）
            start_date: 开始日期（YYYYMMDD）
            end_date: 结束日期（YYYYMMDD）

        Returns:
            同步结果

        Examples:
            >>> service = MarginSecsService()
            >>> result = await service.sync_margin_secs(trade_date='20240417')
        """
        try:
            logger.info(f"开始同步融资融券标的: trade_date={trade_date}, exchange={exchange}")

            # 1. 从 Tushare 获取数据
            df = await self._fetch_from_tushare(
                trade_date=trade_date,
                exchange=exchange,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 保存到数据库
            records = await asyncio.to_thread(
                self.margin_secs_repo.bulk_upsert, df
            )

            logger.info(f"成功同步 {records} 条融资融券标的记录")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条记录",
                "records": records,
                "date_range": {
                    "start": df['trade_date'].min(),
                    "end": df['trade_date'].max()
                }
            }

        except Exception as e:
            logger.error(f"同步融资融券标的失败: {e}")
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "records": 0
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
        strategy: str = 'by_month',
        update_state_fn=None,
        max_requests_per_minute: int = 0
    ) -> Dict:
        """按自然月切片全量同步融资融券标的历史数据（支持 Redis 续继）

        Redis Key: sync:margin_secs:full_history:progress
        margin_secs 每日约 3000 条标的，月内重复率高，按月切片后用 limit/offset 分页保障完整性。
        """
        FULL_HISTORY_START_DATE = "20100101"
        PROGRESS_KEY = "sync:margin_secs:full_history:progress"
        PAGE_SIZE = 3000
        MAX_OFFSET = 100_000

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量margin_secs] 共 {total} 个月度片段")

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
                    all_frames = []
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(f"[全量margin_secs] {ms}-{me} offset 达上限，停止分页")
                            break
                        df = await asyncio.to_thread(
                            provider.api_client.pro.margin_secs,
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
                        records = await asyncio.to_thread(self.margin_secs_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量margin_secs] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量margin_secs] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count, 'skipped': skip_count,
            'errors': error_count, 'records': total_records,
            'total_segments': total
        }

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日

        Returns:
            YYYY-MM-DD 格式的日期，或 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.margin_secs_repo.exists_by_date, today)
        if has_today:
            return self._format_date_for_display(today)
        latest = await asyncio.to_thread(self.margin_secs_repo.get_latest_trade_date)
        if latest:
            return self._format_date_for_display(latest)
        return None

    async def get_margin_secs_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Dict:
        """
        获取融资融券标的数据（单日筛选 + 分页）

        Args:
            trade_date: 交易日期（YYYY-MM-DD 或 YYYYMMDD），为空时自动解析最近有数据的交易日
            ts_code: 标的代码
            exchange: 交易所代码
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据、统计信息、总数、回填的交易日期
        """
        try:
            # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            # 未指定日期时自动解析最近有数据的交易日
            resolved_date: Optional[str] = None
            if not trade_date_fmt:
                resolved_date = await self.resolve_default_trade_date()
                if resolved_date:
                    trade_date_fmt = resolved_date.replace('-', '')
            else:
                resolved_date = self._format_date_for_display(trade_date_fmt)

            if not trade_date_fmt:
                return {
                    "items": [],
                    "statistics": {},
                    "total": 0,
                    "trade_date": None
                }

            offset = (page - 1) * page_size

            # 并发获取数据、总数、统计
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.margin_secs_repo.get_by_trade_date_paged,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    exchange=exchange,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.margin_secs_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    exchange=exchange
                ),
                asyncio.to_thread(
                    self.margin_secs_repo.get_statistics,
                    start_date=trade_date_fmt,
                    end_date=trade_date_fmt,
                    exchange=exchange
                )
            )

            # 日期格式转换用于显示（YYYYMMDD -> YYYY-MM-DD）
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date_for_display(item['trade_date'])

            return {
                "items": items,
                "statistics": statistics,
                "total": total,
                "trade_date": resolved_date
            }

        except Exception as e:
            logger.error(f"获取融资融券标的数据失败: {e}")
            raise

    async def get_latest_data(self, exchange: Optional[str] = None) -> Dict:
        """
        获取最新交易日的数据

        Args:
            exchange: 交易所代码（可选）

        Returns:
            最新数据
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.margin_secs_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "statistics": {},
                    "trade_date": None
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.margin_secs_repo.get_by_trade_date,
                trade_date=latest_date,
                exchange=exchange
            )

            # 获取交易所分布
            distribution = await asyncio.to_thread(
                self.margin_secs_repo.get_exchange_distribution,
                trade_date=latest_date
            )

            # 日期格式转换
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date_for_display(item['trade_date'])

            return {
                "items": items,
                "statistics": {
                    "total_count": len(items),
                    "trade_date": self._format_date_for_display(latest_date),
                    "exchange_distribution": distribution
                },
                "trade_date": self._format_date_for_display(latest_date)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def _fetch_from_tushare(
        self,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        从 Tushare 获取数据

        Args:
            trade_date: 交易日期
            exchange: 交易所代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame
        """
        try:
            # 准备参数
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if exchange:
                params['exchange'] = exchange
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            logger.info(f"从 Tushare 获取融资融券标的数据，参数: {params}")

            # 获取数据提供者
            provider = self._get_provider()

            # 调用 Tushare API（通过 api_client.pro）
            df = await asyncio.to_thread(
                provider.api_client.pro.margin_secs,
                **params
            )

            logger.info(f"从 Tushare 获取到 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"从 Tushare 获取数据失败: {e}")
            raise

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        try:
            # 检查必需列
            required_columns = ['trade_date', 'ts_code', 'name', 'exchange']
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"缺少必需列: {missing_columns}")

            # 删除重复记录
            before_count = len(df)
            df = df.drop_duplicates(subset=['trade_date', 'ts_code'])
            after_count = len(df)
            if before_count != after_count:
                logger.warning(f"删除了 {before_count - after_count} 条重复记录")

            # 删除空值记录
            df = df.dropna(subset=['trade_date', 'ts_code'])

            # 数据类型转换
            df['trade_date'] = df['trade_date'].astype(str)
            df['ts_code'] = df['ts_code'].astype(str)
            df['name'] = df['name'].astype(str)
            df['exchange'] = df['exchange'].astype(str)

            logger.info(f"数据验证完成，有效记录数: {len(df)}")
            return df

        except Exception as e:
            logger.error(f"数据验证和清洗失败: {e}")
            raise

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于显示（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: YYYYMMDD 格式的日期

        Returns:
            YYYY-MM-DD 格式的日期
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
