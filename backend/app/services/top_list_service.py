"""
龙虎榜每日明细 Service
"""
import asyncio
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger

from app.repositories import TopListRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class TopListService:
    """龙虎榜每日明细业务逻辑层"""

    def __init__(self):
        self.top_list_repo = TopListRepository()
        self.sync_history_repo = SyncHistoryRepository()
        self.calendar_repo = TradingCalendarRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ TopListService initialized")

    async def get_top_list_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 30,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取龙虎榜数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            ts_code: 股票代码
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据字典，包含 items、total、page、page_size
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
        end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

        offset = (page - 1) * page_size

        # 并发查询数据和总条数
        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.top_list_repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                limit=page_size,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            ),
            asyncio.to_thread(
                self.top_list_repo.get_record_count,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取龙虎榜统计信息

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
            self.top_list_repo.get_statistics,
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 金额单位换算（元 -> 万元）
        statistics['avg_net_amount'] = statistics['avg_net_amount'] / 10000
        statistics['total_net_amount'] = statistics['total_net_amount'] / 10000
        statistics['max_net_amount'] = statistics['max_net_amount'] / 10000
        statistics['min_net_amount'] = statistics['min_net_amount'] / 10000
        statistics['avg_amount'] = statistics['avg_amount'] / 10000

        return statistics

    async def get_latest_data(self) -> Dict:
        """
        获取最新交易日的龙虎榜数据

        Returns:
            最新数据字典
        """
        # 获取最新交易日期
        latest_date = await asyncio.to_thread(
            self.top_list_repo.get_latest_trade_date
        )

        if not latest_date:
            return {
                "latest_date": None,
                "items": [],
                "total": 0
            }

        # 获取最新数据
        items = await asyncio.to_thread(
            self.top_list_repo.get_by_trade_date,
            trade_date=latest_date
        )

        # 日期格式转换
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return {
            "latest_date": self._format_date(latest_date),
            "items": items,
            "total": len(items)
        }

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'top_list')
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, 'top_list', 'incremental'
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

        logger.info(f"[top_list] 增量同步 {len(trading_days)} 个交易日 ({start_date}~{end_date})")

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'top_list', 'incremental', 'by_date', start_date,
        )
        try:
            total_records = 0
            for trade_date in trading_days:
                try:
                    result = await self.sync_top_list(trade_date=trade_date)
                    total_records += result.get('records', 0)
                except Exception as e:
                    logger.error(f"[top_list] {trade_date} 同步失败: {e}")

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

    async def sync_top_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        从 Tushare 同步龙虎榜数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选，默认为前一个交易日）
            ts_code: 股票代码（可选）

        Returns:
            同步结果字典
        """
        # 如果没有指定日期，从 trading_calendar 表取最新交易日
        # 注意：top_list 接口的 trade_date 是必需参数，传 None 不会返回最新日期
        if not trade_date:
            trade_date = await asyncio.to_thread(
                self.calendar_repo.get_latest_trading_day
            )
            logger.info(f"未指定日期，使用最新交易日: {trade_date}")

        logger.info(f"开始同步龙虎榜数据: trade_date={trade_date}, ts_code={ts_code}")

        try:
            # 1. 从 Tushare 获取数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_top_list,
                trade_date=trade_date,
                ts_code=ts_code
            )

            if df.empty:
                logger.warning(f"未获取到龙虎榜数据: trade_date={trade_date}")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.top_list_repo.bulk_upsert,
                df
            )

            logger.info(f"✓ 龙虎榜数据同步完成: {records} 条记录")
            return {
                "status": "success",
                "message": f"成功同步 {records} 条龙虎榜记录",
                "records": records,
                "trade_date": trade_date
            }

        except Exception as e:
            logger.error(f"同步龙虎榜数据失败: {e}")
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "records": 0
            }

    async def get_top_by_net_amount(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取净买入额排名TOP数据

        Args:
            trade_date: 交易日期，格式：YYYY-MM-DD
            limit: 返回记录数

        Returns:
            排名数据列表
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        trade_date_fmt = trade_date.replace('-', '') if trade_date else None

        # 获取排名数据
        items = await asyncio.to_thread(
            self.top_list_repo.get_top_by_net_amount,
            trade_date=trade_date_fmt,
            limit=limit
        )

        # 日期格式转换
        for item in items:
            if item['trade_date']:
                item['trade_date'] = self._format_date(item['trade_date'])

        # 金额单位换算（元 -> 万元）
        for item in items:
            if item['amount'] is not None:
                item['amount'] = item['amount'] / 10000
            if item['l_sell'] is not None:
                item['l_sell'] = item['l_sell'] / 10000
            if item['l_buy'] is not None:
                item['l_buy'] = item['l_buy'] / 10000
            if item['l_amount'] is not None:
                item['l_amount'] = item['l_amount'] / 10000
            if item['net_amount'] is not None:
                item['net_amount'] = item['net_amount'] / 10000
            if item['float_values'] is not None:
                item['float_values'] = item['float_values'] / 10000

        return items

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        未指定日期时解析默认交易日：
        先查今天是否有数据，无则回退到数据库中最近有数据的交易日。

        Returns:
            日期字符串，格式：YYYY-MM-DD；若无任何数据返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        count = await asyncio.to_thread(
            self.top_list_repo.get_record_count,
            start_date=today,
            end_date=today
        )
        if count > 0:
            return self._format_date(today)

        latest = await asyncio.to_thread(self.top_list_repo.get_latest_trade_date)
        return self._format_date(latest) if latest else None

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
        """逐交易日全量同步龙虎榜每日明细历史数据（支持 Redis 续继）

        top_list 接口只接受 trade_date（必需），不支持日期范围，必须逐日请求。
        Redis Key: sync:top_list:full_history:progress
        Redis 续继 Key 格式："{trade_date}"（每个交易日）
        """
        FULL_HISTORY_START_DATE = "20050101"
        PROGRESS_KEY = "sync:top_list:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_days = await asyncio.to_thread(
            self.calendar_repo.get_trading_days_between, effective_start, today
        )
        total = len(all_days)
        logger.info(f"[全量top_list] 共 {total} 个交易日")

        completed_set = redis_client.smembers(PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [d for d in all_days if d not in completed_set]
        skip_count = len(all_days) - len(pending)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider()
        sem = asyncio.Semaphore(max(1, concurrency))

        async def sync_day(trade_date: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_top_list,
                        trade_date=trade_date
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.top_list_repo.bulk_upsert, df)
                    return trade_date, True, records, None
                except Exception as e:
                    logger.warning(f"[全量top_list] {trade_date} 失败: {e}")
                    return trade_date, False, 0, str(e)

        BATCH_SIZE = concurrency * 4
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            results = await asyncio.gather(*[sync_day(d) for d in batch])

            for trade_date, ok, records, _err in results:
                if ok:
                    redis_client.sadd(PROGRESS_KEY, trade_date)
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
            logger.info(f"[全量top_list] 全部完成，已清除进度记录")

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
        数据验证和清洗

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 删除重复数据
        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')

        # 处理缺失值
        numeric_columns = [
            'close', 'pct_change', 'turnover_rate', 'amount',
            'l_sell', 'l_buy', 'l_amount', 'net_amount',
            'net_rate', 'amount_rate', 'float_values'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 确保必需列存在
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 删除 trade_date 或 ts_code 为空的记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        logger.info(f"数据清洗完成，保留 {len(df)} 条有效记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期字符串（YYYYMMDD -> YYYY-MM-DD）

        Args:
            date_str: 日期字符串，格式：YYYYMMDD

        Returns:
            格式化后的日期字符串，格式：YYYY-MM-DD
        """
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
