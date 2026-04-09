"""
融资融券交易汇总服务

提供融资融券交易汇总数据的同步和查询功能
数据来源：Tushare Pro margin 接口
积分消耗：2000分/次
"""

import asyncio
import calendar
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, date
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import MarginRepository


class MarginService:
    """融资融券交易汇总服务"""

    def __init__(self):
        self.margin_repo = MarginRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_margin(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券交易汇总数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步融资融券交易汇总: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, exchange_id={exchange_id}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_margin,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date,
                exchange_id=exchange_id
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到融资融券交易汇总数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await self._insert_margin_data(df)

            logger.info(f"成功同步融资融券交易汇总数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条融资融券交易汇总数据"
            }

        except Exception as e:
            logger.error(f"同步融资融券交易汇总失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        # 移除空行
        df = df.dropna(subset=['trade_date', 'exchange_id'])

        # 确保必需字段存在
        required_columns = ['trade_date', 'exchange_id']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 数值字段转换
        numeric_columns = ['rzye', 'rzmre', 'rzche', 'rqye', 'rqmcl', 'rzrqye', 'rqyl']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 移除所有数值字段都为空的行
        df = df.dropna(subset=numeric_columns, how='all')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    async def _insert_margin_data(self, df: pd.DataFrame) -> int:
        """
        插入融资融券交易汇总数据到数据库

        Args:
            df: 数据DataFrame

        Returns:
            插入的记录数
        """
        if len(df) == 0:
            return 0

        # 使用 Repository 批量插入
        records = await asyncio.to_thread(self.margin_repo.bulk_upsert, df)
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
        """按自然月切片全量同步融资融券交易汇总历史数据（支持 Redis 续继）

        Redis Key: sync:margin:full_history:progress
        """
        FULL_HISTORY_START_DATE = "20100101"
        PROGRESS_KEY = "sync:margin:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量margin] 共 {total} 个月度片段")

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
                        provider.get_margin,
                        start_date=ms,
                        end_date=me,
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.margin_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量margin] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量margin] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count, 'skipped': skip_count,
            'errors': error_count, 'records': total_records,
            'total_segments': total
        }

    async def resolve_default_date_range(self) -> Dict[str, Optional[str]]:
        """
        解析默认日期范围：返回表中最新交易日（YYYY-MM-DD），用于前端回填

        Returns:
            {'latest_date': 'YYYY-MM-DD' or None}
        """
        try:
            latest = await asyncio.to_thread(self.margin_repo.get_latest_trade_date)
            if latest:
                d = str(latest)
                return {'latest_date': f"{d[:4]}-{d[4:6]}-{d[6:8]}"}
            return {'latest_date': None}
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return {'latest_date': None}

    async def get_margin_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        查询融资融券交易汇总数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            exchange_id: 交易所代码
            page: 页码
            page_size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向 asc/desc

        Returns:
            包含数据、总数、统计信息的字典
        """
        try:
            # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 计算分页参数
            offset = (page - 1) * page_size

            # 并发查数据、总数、统计
            data, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.margin_repo.get_by_date_range,
                    start_date_fmt,
                    end_date_fmt,
                    exchange_id=exchange_id,
                    limit=page_size,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.margin_repo.get_record_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    exchange_id=exchange_id
                ),
                asyncio.to_thread(
                    self.margin_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    exchange_id=exchange_id
                )
            )

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"查询融资融券交易汇总数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取融资融券交易汇总统计数据

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
                self.margin_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取融资融券统计数据失败: {str(e)}")
            raise
