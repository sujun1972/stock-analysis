"""
涨跌停列表服务层

负责涨跌停列表数据的业务逻辑处理
"""

import asyncio
import calendar
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, date
from loguru import logger

from app.repositories import LimitListRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class LimitListService:
    """涨跌停列表服务类"""

    def __init__(self):
        """初始化涨跌停列表服务"""
        self.limit_list_repo = LimitListRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ LimitListService initialized")

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
        """按自然月切片全量同步涨跌停列表历史数据（支持 Redis 续继）

        Redis Key: sync:limit_list:full_history:progress
        """
        FULL_HISTORY_START_DATE = "20100101"
        PROGRESS_KEY = "sync:limit_list:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量limit_list] 共 {total} 个月度片段")

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
                    PAGE_SIZE = 2500
                    all_frames = []
                    offset = 0
                    while True:
                        if offset >= MAX_OFFSET:
                            logger.warning(f"[全量limit_list] {ms}-{me} offset 达上限，停止分页")
                            break
                        df = await asyncio.to_thread(
                            provider.get_limit_list_d,
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
                        records = await asyncio.to_thread(self.limit_list_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量limit_list] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量limit_list] 全部完成，已清除进度记录")

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

    def _format_date(self, date_str: str) -> str:
        """将 YYYYMMDD 转为 YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    async def resolve_default_trade_date(self) -> Optional[str]:
        """
        未指定日期时解析默认交易日：
        先查今天是否有数据，无则回退到数据库中最近有数据的交易日。

        Returns:
            日期字符串，格式：YYYY-MM-DD；若无任何数据返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        count = await asyncio.to_thread(
            self.limit_list_repo.get_record_count,
            start_date=today,
            end_date=today
        )
        if count > 0:
            return self._format_date(today)

        latest = await asyncio.to_thread(self.limit_list_repo.get_latest_trade_date)
        return self._format_date(latest) if latest else None

    async def sync_limit_list(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None
    ) -> Dict:
        """
        同步涨跌停列表数据

        Args:
            trade_date: 单个交易日期，格式：YYYYMMDD
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步涨跌停列表数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, limit_type={limit_type}")

            # limit_list_d 单次上限 2500 条，需翻页
            MAX_OFFSET = 100_000
            PAGE_SIZE = 2500
            provider = self._get_provider()
            all_frames = []
            offset = 0

            while True:
                if offset >= MAX_OFFSET:
                    logger.warning(f"[limit_list] offset 已达 {MAX_OFFSET} 上限，停止分页")
                    break
                df = await asyncio.to_thread(
                    provider.get_limit_list_d,
                    trade_date=trade_date,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    limit_type=limit_type,
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
                logger.warning("未获取到涨跌停列表数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            df = pd.concat(all_frames, ignore_index=True)
            logger.info(f"从Tushare获取到 {len(df)} 条涨跌停列表数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.limit_list_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条涨跌停列表数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步涨跌停列表数据失败: {str(e)}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e),
                "message": "同步失败"
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: pandas DataFrame

        Returns:
            清洗后的 DataFrame
        """
        # 确保必需字段存在
        required_fields = ['trade_date', 'ts_code']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        # 移除空值记录
        df = df.dropna(subset=['trade_date', 'ts_code'])

        # 数据类型转换
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str)

        if 'ts_code' in df.columns:
            df['ts_code'] = df['ts_code'].astype(str)

        # 移除重复记录
        df = df.drop_duplicates(subset=['trade_date', 'ts_code'], keep='last')

        logger.debug(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    async def get_limit_list_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> Dict:
        """
        获取涨跌停列表数据（支持分页和排序）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）
            page: 页码（从1开始）
            page_size: 每页记录数
            sort_by: 排序字段
            sort_order: 排序方向（asc/desc）

        Returns:
            数据字典
        """
        # 并发查询数据和总数
        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.limit_list_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                limit_type=limit_type,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order
            ),
            asyncio.to_thread(
                self.limit_list_repo.get_count_by_date_range,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                limit_type=limit_type
            )
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item.get('trade_date'):
                item['trade_date'] = self._format_date(item['trade_date'])

        # 获取统计信息
        statistics = await asyncio.to_thread(
            self.limit_list_repo.get_statistics,
            start_date=start_date,
            end_date=end_date,
            limit_type=limit_type
        )

        return {
            'items': items,
            'statistics': statistics,
            'total': total
        }

    async def get_latest_data(self, limit_type: Optional[str] = None) -> Dict:
        """
        获取最新涨跌停列表数据

        Args:
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）

        Returns:
            最新数据字典
        """
        # 获取最新交易日期
        latest_date = await asyncio.to_thread(
            self.limit_list_repo.get_latest_trade_date
        )

        if not latest_date:
            return {
                'items': [],
                'statistics': {},
                'total': 0,
                'trade_date': None
            }

        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.limit_list_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit_type=limit_type,
                page=1,
                page_size=1000
            ),
            asyncio.to_thread(
                self.limit_list_repo.get_count_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit_type=limit_type
            )
        )

        for item in items:
            if item.get('trade_date'):
                item['trade_date'] = self._format_date(item['trade_date'])

        statistics = await asyncio.to_thread(
            self.limit_list_repo.get_statistics,
            start_date=latest_date,
            end_date=latest_date,
            limit_type=limit_type
        )

        return {
            'items': items,
            'statistics': statistics,
            'total': total,
            'trade_date': self._format_date(latest_date)
        }

    async def get_top_limit_up_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取涨停股票排行

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（None表示最新日期）
            limit: 返回记录数限制

        Returns:
            涨停股票列表
        """
        # 如果未指定日期，获取最新日期
        if not trade_date:
            trade_date = await asyncio.to_thread(
                self.limit_list_repo.get_latest_trade_date
            )
            if not trade_date:
                return []

        # 获取涨停股票排行
        items = await asyncio.to_thread(
            self.limit_list_repo.get_top_limit_up_stocks,
            trade_date=trade_date,
            limit=limit
        )

        # 数据格式转换（get_top_limit_up_stocks 返回原始 tuple）
        formatted_items = []
        for item in items:
            formatted_items.append({
                'trade_date': self._format_date(item[0]) if item[0] else None,
                'ts_code': item[1],
                'industry': item[2],
                'name': item[3],
                'close': float(item[4]) if item[4] else None,
                'pct_chg': float(item[5]) if item[5] else None,
                'amount': float(item[6]) if item[6] else None,
                'fd_amount': float(item[7]) if item[7] else None,
                'first_time': item[8],
                'last_time': item[9],
                'open_times': item[10],
                'up_stat': item[11],
                'limit_times': item[12],
                'limit_type': item[13],
            })

        return formatted_items
