"""
融资融券交易明细服务

提供融资融券交易明细数据的同步和查询功能
数据来源：Tushare Pro margin_detail 接口
积分消耗：2000分/次
单次限制：最大6000行
"""

import asyncio
import calendar
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
import pandas as pd
from loguru import logger

from app.repositories import MarginDetailRepository
from app.repositories.margin_secs_repository import MarginSecsRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.stock_quote_cache import stock_quote_cache
from app.services.tushare_sync_base import TushareSyncBase


class MarginDetailService(TushareSyncBase):
    """融资融券交易明细服务"""

    TABLE_KEY = 'margin_detail'

    def __init__(self):
        super().__init__()
        self.margin_detail_repo = MarginDetailRepository()
        self.margin_secs_repo = MarginSecsRepository()
        self.sync_history_repo = SyncHistoryRepository()

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'margin_detail')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'margin_detail', 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步（通过基类 run_incremental_sync 实现自动切片+翻页）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        if start_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_margin_detail,
            upsert_fn=self.margin_detail_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
        )

    async def sync_margin_detail(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券交易明细数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            ts_code: TS股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步融资融券交易明细: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近一个交易日
            if not trade_date and not start_date and not end_date:
                # 获取最近一个交易日
                trade_date = await self._get_latest_trade_date()
                logger.info(f"未指定日期，默认同步最近交易日: {trade_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_margin_detail,
                trade_date=trade_date,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到融资融券交易明细数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_margin_detail_data(df)

            logger.info(f"成功同步融资融券交易明细数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条融资融券交易明细数据"
            }

        except Exception as e:
            logger.error(f"同步融资融券交易明细失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    async def _get_latest_trade_date(self) -> str:
        """
        获取最近一个交易日

        Returns:
            交易日期 YYYYMMDD
        """
        try:
            # 使用 Repository 获取最近交易日
            latest_date = await asyncio.to_thread(
                self.margin_detail_repo.get_latest_trade_date
            )

            if latest_date:
                return latest_date
            else:
                # 如果没有数据，返回前一天
                return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            # 返回前一天作为默认值
            return (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 移除空行
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 确保必需字段存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 数值字段转换
        numeric_columns = ['rzye', 'rqye', 'rzmre', 'rqyl', 'rzche', 'rqchl', 'rqmcl', 'rzrqye']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 移除所有数值字段都为空的行
        df = df.dropna(subset=numeric_columns, how='all')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_margin_detail_data(self, df: pd.DataFrame) -> int:
        """
        插入融资融券交易明细数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 使用 Repository 批量插入
        records = await asyncio.to_thread(self.margin_detail_repo.bulk_upsert, df)
        return records

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
        """按自然月切片全量同步融资融券交易明细历史数据（支持 Redis 续继）

        Redis Key: sync:margin_detail:full_history:progress
        每月约 5000~6000 条，接近单次上限，需分页。
        """
        FULL_HISTORY_START_DATE = "20100101"
        PROGRESS_KEY = "sync:margin_detail:full_history:progress"
        PAGE_SIZE = 3000
        MAX_OFFSET = 100_000

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量margin_detail] 共 {total} 个月度片段")

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
                            logger.warning(f"[全量margin_detail] {ms}-{me} offset 达上限，停止分页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_margin_detail,
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
                        records = await asyncio.to_thread(self.margin_detail_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量margin_detail] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量margin_detail] 全部完成，已清除进度记录")

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
            YYYY-MM-DD 格式日期字符串，或 None
        """
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.margin_detail_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.margin_detail_repo.get_latest_trade_date)
        if latest:
            d = str(latest)
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        return None

    async def get_margin_detail_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询融资融券交易明细数据

        Args:
            trade_date: 交易日期 YYYY-MM-DD（单日筛选）
            ts_code: 股票代码
            page: 页码
            page_size: 每页数量

        Returns:
            包含数据、统计和 trade_date 的字典
        """
        try:
            # 未传日期时解析最近有数据的交易日
            resolved_date = trade_date
            if not resolved_date:
                resolved_date = await self.resolve_default_trade_date()

            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            date_fmt = resolved_date.replace('-', '') if resolved_date else None

            # 计算分页参数
            offset = (page - 1) * page_size

            # 并发查数据、总数、统计
            data, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.margin_detail_repo.get_by_date_range,
                    date_fmt,
                    date_fmt,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.margin_detail_repo.get_record_count,
                    start_date=date_fmt,
                    end_date=date_fmt,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.margin_detail_repo.get_statistics,
                    start_date=date_fmt,
                    end_date=date_fmt
                )
            )

            # 注入标的名称（股票从 StockQuoteCache，ETF/基金从 margin_secs 回退）
            if data:
                ts_codes = list(dict.fromkeys(item['ts_code'] for item in data))
                quotes = await asyncio.to_thread(stock_quote_cache._repo.get_quotes, ts_codes)
                # 找出无名称的代码，从 margin_secs 补充（ETF/基金）
                missing_codes = [
                    code for code in ts_codes
                    if not quotes.get(code, {}).get('name')
                ]
                etf_name_map: dict = {}
                if missing_codes:
                    etf_name_map = await asyncio.to_thread(
                        self.margin_secs_repo.get_name_map, missing_codes
                    )
                for item in data:
                    name = quotes.get(item['ts_code'], {}).get('name', '')
                    if not name:
                        name = etf_name_map.get(item['ts_code'], '') or item.get('name', '')
                    item['name'] = name

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "statistics": statistics,
                "trade_date": resolved_date
            }

        except Exception as e:
            logger.error(f"查询融资融券交易明细数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取融资融券交易明细统计数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计数据字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 使用 Repository 获取统计数据
            stats = await asyncio.to_thread(
                self.margin_detail_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取融资融券明细统计数据失败: {str(e)}")
            raise

    async def get_top_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取融资融券余额TOP股票

        Args:
            trade_date: 交易日期 YYYY-MM-DD
            limit: 返回数量

        Returns:
            TOP股票列表
        """
        try:
            # 如果未指定日期，获取最新交易日
            if not trade_date:
                latest_date = await asyncio.to_thread(
                    self.margin_detail_repo.get_latest_trade_date
                )
                # 将 datetime.date 对象转换为字符串
                if latest_date:
                    from datetime import date
                    if isinstance(latest_date, date):
                        trade_date = latest_date.strftime('%Y%m%d')
                    else:
                        trade_date = latest_date

            if not trade_date:
                return []

            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            if isinstance(trade_date, str):
                trade_date_formatted = trade_date.replace('-', '') if '-' in trade_date else trade_date
            else:
                trade_date_formatted = trade_date

            # 使用 Repository 查询 TOP 股票
            top_stocks = await asyncio.to_thread(
                self.margin_detail_repo.get_top_by_rzrqye,
                trade_date=trade_date_formatted,
                limit=limit
            )

            return top_stocks

        except Exception as e:
            logger.error(f"获取TOP股票失败: {str(e)}")
            raise
