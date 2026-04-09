"""
转融资交易汇总服务

提供转融通融资汇总数据的同步和查询功能
数据来源：Tushare Pro slb_len 接口
积分消耗：2000分/分钟200次，5000分500次
单次限量：最大5000行
"""

import asyncio
import calendar
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, date
import pandas as pd
from loguru import logger

from core.src.providers import DataProviderFactory
from app.core.config import settings
from app.repositories import SlbLenRepository


class SlbLenService:
    """转融资交易汇总服务"""

    def __init__(self):
        self.slb_len_repo = SlbLenRepository()
        self.provider_factory = DataProviderFactory()

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def sync_slb_len(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步转融资交易汇总数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步转融资交易汇总: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 如果没有指定任何日期，默认同步最近30天
            if not trade_date and not start_date and not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                logger.info(f"未指定日期，默认同步最近30天: {start_date} ~ {end_date}")

            # 获取数据提供者
            provider = self._get_provider()

            # 从Tushare获取数据
            df = await asyncio.to_thread(
                provider.get_slb_len,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                logger.warning("未获取到转融资交易汇总数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "无数据需要同步"
                }

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 插入数据库
            records = await asyncio.to_thread(
                self.slb_len_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步转融资交易汇总数据 {records} 条")
            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条转融资交易汇总数据"
            }

        except Exception as e:
            logger.error(f"同步转融资交易汇总失败: {str(e)}")
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
        df = df.dropna(subset=['trade_date'])

        # 确保必需字段存在
        if 'trade_date' not in df.columns:
            raise ValueError("数据缺少必需字段: trade_date")

        # 确保数值列类型正确
        numeric_columns = ['ob', 'auc_amount', 'repo_amount', 'repay_amount', 'cb']
        for col in numeric_columns:
            if col in df.columns:
                # 将None转换为0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return df

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
        """按自然月切片全量同步转融资交易汇总历史数据（支持 Redis 续继）

        Redis Key: sync:slb_len:full_history:progress
        slb_len 每月约 20 条，远低于上限，不需要分页。
        """
        FULL_HISTORY_START_DATE = "20130101"
        PROGRESS_KEY = "sync:slb_len:full_history:progress"

        effective_start = start_date or FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")

        all_segments = self._generate_months(effective_start, today)
        total = len(all_segments)
        logger.info(f"[全量slb_len] 共 {total} 个月度片段")

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
                        provider.get_slb_len,
                        start_date=ms,
                        end_date=me,
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.slb_len_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    logger.warning(f"[全量slb_len] 片段 {ms}-{me} 失败: {e}")
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
            logger.info(f"[全量slb_len] 全部完成，已清除进度记录")

        return {
            'status': 'success',
            'success': success_count, 'skipped': skip_count,
            'errors': error_count, 'records': total_records,
            'total_segments': total
        }

    async def get_slb_len_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        查询转融资交易汇总数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            limit: 返回记录数

        Returns:
            查询结果字典
        """
        try:
            # 日期格式转换 YYYY-MM-DD -> YYYYMMDD
            start_date_formatted = start_date.replace('-', '') if start_date else None
            end_date_formatted = end_date.replace('-', '') if end_date else None

            # 如果没有指定日期，默认查询最近30天
            if not start_date_formatted and not end_date_formatted:
                end_date_formatted = datetime.now().strftime('%Y%m%d')
                start_date_formatted = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            # 查询数据
            items = await asyncio.to_thread(
                self.slb_len_repo.get_by_date_range,
                start_date=start_date_formatted or '19900101',
                end_date=end_date_formatted or '29991231',
                limit=limit
            )

            # 日期格式转换 YYYYMMDD -> YYYY-MM-DD (用于前端显示)
            for item in items:
                if 'trade_date' in item and item['trade_date']:
                    item['trade_date'] = self._format_date_for_display(item['trade_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"查询转融资数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取转融资统计数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计数据字典
        """
        try:
            # 日期格式转换
            start_date_formatted = start_date.replace('-', '') if start_date else None
            end_date_formatted = end_date.replace('-', '') if end_date else None

            # 查询统计数据
            stats = await asyncio.to_thread(
                self.slb_len_repo.get_statistics,
                start_date=start_date_formatted,
                end_date=end_date_formatted
            )

            return stats

        except Exception as e:
            logger.error(f"获取转融资统计失败: {str(e)}")
            raise

    async def get_latest_data(self) -> Optional[Dict]:
        """
        获取最新交易日的转融资数据

        Returns:
            最新数据，如果不存在则返回None
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(
                self.slb_len_repo.get_latest_trade_date
            )

            if not latest_date:
                return None

            # 获取该日期的数据
            data = await asyncio.to_thread(
                self.slb_len_repo.get_by_trade_date,
                latest_date
            )

            if data and 'trade_date' in data:
                data['trade_date'] = self._format_date_for_display(data['trade_date'])

            return data

        except Exception as e:
            logger.error(f"获取最新转融资数据失败: {str(e)}")
            return None

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于显示

        Args:
            date_str: YYYYMMDD 格式的日期字符串

        Returns:
            YYYY-MM-DD 格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            return date_str
