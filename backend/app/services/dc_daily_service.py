"""
东方财富概念板块行情服务

处理东方财富概念板块行情数据的业务逻辑
"""

import asyncio
import calendar
import pandas as pd
import traceback
from datetime import datetime, date, timedelta
from typing import Optional, Dict
from loguru import logger

from app.repositories.dc_daily_repository import DcDailyRepository
from app.repositories.dc_index_repository import DcIndexRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class DcDailyService:
    """东方财富概念板块行情服务"""

    def __init__(self):
        self.dc_daily_repo = DcDailyRepository()
        self.dc_index_repo = DcIndexRepository()
        self.provider_factory = DataProviderFactory()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ DcDailyService initialized")

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

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'dc_daily')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'dc_daily', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(self, start_date=None, end_date=None, sync_strategy=None, max_requests_per_minute=None) -> Dict:
        """增量同步（按日期范围拉取并记录 sync_history）"""
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, 'dc_daily', 'incremental', 'by_date_range', start_date,
        )
        try:
            result = await self.sync_dc_daily(start_date=start_date, end_date=end_date)
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'success', result.get('records', 0), end_date, None,
            )
            return result
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete, history_id, 'failure', 0, None, str(e),
            )
            raise

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        update_state_fn=None
    ) -> Dict:
        """按自然月切片全量同步东方财富概念板块行情历史数据（支持 Redis 续继）

        Redis Key: sync:dc_daily:full_history:progress
        """
        FULL_HISTORY_START_DATE = "20160101"
        PROGRESS_KEY = "sync:dc_daily:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量dc_daily] 共 {total} 个月度片段")

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
                            logger.warning(f"[全量dc_daily] {ms}-{me} offset 达上限，停止分页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_dc_daily,
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
                        records = await asyncio.to_thread(self.dc_daily_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量dc_daily] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量dc_daily] 全部完成，已清除进度记录")

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

    async def sync_dc_daily(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None
    ) -> Dict:
        """
        同步东方财富概念板块行情数据

        Args:
            ts_code: 板块代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            idx_type: 板块类型（概念板块/行业板块/地域板块，可选）

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步东方财富概念板块行情数据: ts_code={ts_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}, idx_type={idx_type}")

            # 1. 从 Tushare 获取数据（分页，单次上限 2000 条）
            MAX_OFFSET = 100_000
            PAGE_SIZE = 2000
            provider = self._get_provider()
            all_frames = []
            offset = 0
            while True:
                if offset >= MAX_OFFSET:
                    logger.warning(f"[dc_daily] offset 已达 {MAX_OFFSET} 上限，停止分页")
                    break
                df = await asyncio.to_thread(
                    provider.get_dc_daily,
                    ts_code=ts_code,
                    trade_date=trade_date,
                    start_date=start_date,
                    end_date=end_date,
                    idx_type=idx_type,
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
                logger.warning(f"未获取到东方财富概念板块行情数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            df = pd.concat(all_frames, ignore_index=True)
            logger.info(f"从 Tushare 获取到 {len(df)} 条东方财富概念板块行情数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库（使用 Repository）
            records = await asyncio.to_thread(
                self.dc_daily_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条东方财富概念板块行情数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步东方财富概念板块行情数据失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        try:
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            df = df.dropna(subset=required_fields)

            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            if 'ts_code' in df.columns:
                df['ts_code'] = df['ts_code'].astype(str)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    @staticmethod
    def _format_date(date_str: Optional[str]) -> Optional[str]:
        """将 YYYYMMDD 格式转换为 YYYY-MM-DD"""
        if date_str and len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        return date_str

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        未指定日期时解析默认交易日：先查今天是否有数据，无则回退到最近有数据的交易日。

        Returns:
            日期字符串，格式：YYYY-MM-DD；若无任何数据返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        count = await asyncio.to_thread(
            self.dc_daily_repo.get_record_count,
            start_date=today,
            end_date=today
        )
        if count > 0:
            return self._format_date(today)
        latest = await asyncio.to_thread(self.dc_daily_repo.get_latest_trade_date)
        return self._format_date(latest) if latest else None

    async def get_dc_daily_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取东方财富概念板块行情数据

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）
            page: 页码
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            包含数据列表和总数的字典
        """
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            offset = (page - 1) * page_size

            items, total, board_name_map = await asyncio.gather(
                asyncio.to_thread(
                    self.dc_daily_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.dc_daily_repo.get_record_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                ),
                asyncio.to_thread(self.dc_index_repo.get_board_name_map)
            )

            # 格式化日期字段并注入板块名称
            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])
                item['board_name'] = board_name_map.get(item['ts_code'], '')

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取东方财富概念板块行情数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取板块行情数据统计信息

        Args:
            ts_code: 板块代码
            start_date: 开始日期（YYYY-MM-DD）
            end_date: 结束日期（YYYY-MM-DD）

        Returns:
            统计信息字典
        """
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.dc_daily_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return stats

        except Exception as e:
            logger.error(f"获取板块行情统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新的板块行情数据

        Returns:
            最新数据
        """
        try:
            latest_date = await asyncio.to_thread(
                self.dc_daily_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "trade_date": None,
                    "data": []
                }

            items = await asyncio.to_thread(
                self.dc_daily_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            return {
                "trade_date": latest_date,
                "data": items
            }

        except Exception as e:
            logger.error(f"获取最新板块行情数据失败: {e}")
            raise
