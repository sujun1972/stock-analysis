"""
限售股解禁服务

处理限售股解禁数据的业务逻辑
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta, date
from loguru import logger
import pandas as pd

from app.repositories.share_float_repository import ShareFloatRepository
from core.src.providers import DataProviderFactory


class ShareFloatService:
    """限售股解禁服务"""

    FULL_HISTORY_START_DATE = "20050101"
    FULL_HISTORY_PROGRESS_KEY = "sync:share_float:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:share_float:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        self.share_float_repo = ShareFloatRepository()
        self.provider_factory = DataProviderFactory()

    @staticmethod
    def _generate_months(start_date: str, end_date: str) -> list:
        """将日期范围切分为自然月片段，每片返回 (month_start, month_end)，均为 YYYYMMDD。"""
        import calendar
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

    async def sync_full_history(self, redis_client, start_date: Optional[str] = None, update_state_fn=None) -> Dict:
        """按月切片全量同步限售股解禁历史数据（支持 Redis 续继）

        share_float 单次上限6000条，按年切片严重截断（每年可能超过6000条），改为按月切片。
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        segments = self._generate_months(effective_start, today)
        total = len(segments)
        logger.info(f"[全量share_float] 共 {total} 个月段需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [(ms, me) for ms, me in segments if ms not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider()
        sem = asyncio.Semaphore(self.FULL_HISTORY_CONCURRENCY)

        async def sync_month(ms: str, me: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(provider.get_share_float, start_date=ms, end_date=me)
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.share_float_repo.bulk_upsert, df)
                    return ms, me, True, records, None
                except Exception as e:
                    return ms, me, False, 0, str(e)

        BATCH_SIZE = self.FULL_HISTORY_CONCURRENCY * 2
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_month(ms, me) for ms, me in batch])
            for ms, me, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ms)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量share_float] {ms}~{me} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': done, 'total': total,
                    'percent': round(done / total * 100, 1), 'records': total_records, 'errors': error_count})
            logger.info(f"[全量share_float] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量share_float] ✅ 全量同步完成，进度已清除")

        return {"status": "success", "total": total, "success": success_count,
                "skipped": skip_count, "errors": error_count, "records": total_records,
                "message": f"同步完成 {success_count} 个月段，入库 {total_records} 条，失败 {error_count} 个"}

    async def get_share_float_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取限售股解禁数据

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码
            ann_date: 公告日期，格式：YYYYMMDD
            float_date: 解禁日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            包含数据列表和总数的字典
        """
        try:
            # 查询数据
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.share_float_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    ann_date=ann_date,
                    float_date=float_date,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.share_float_repo.get_count,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                )
            )

            # 格式化数据
            for item in items:
                # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])

                # 数值格式化
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取限售股解禁数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取限售股解禁统计信息

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码

        Returns:
            统计信息字典
        """
        try:
            stats = await asyncio.to_thread(
                self.share_float_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )

            # 单位转换和格式化
            stats['total_float_share_yi'] = round(stats['total_float_share'] / 100000000, 2)  # 股 -> 亿股
            stats['avg_float_ratio_percent'] = round(stats['avg_float_ratio'] * 100, 2)  # 比例 -> 百分比
            stats['max_float_ratio_percent'] = round(stats['max_float_ratio'] * 100, 2)

            return stats

        except Exception as e:
            logger.error(f"获取限售股解禁统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict:
        """
        获取最新的限售股解禁数据

        Args:
            ts_code: 股票代码

        Returns:
            最新数据字典
        """
        try:
            # 获取最新解禁日期
            latest_date = await asyncio.to_thread(
                self.share_float_repo.get_latest_float_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {
                    "latest_date": None,
                    "items": []
                }

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.share_float_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=100
            )

            # 格式化数据
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {
                "latest_date": self._format_date(latest_date),
                "items": items
            }

        except Exception as e:
            logger.error(f"获取最新限售股解禁数据失败: {e}")
            raise

    async def sync_share_float(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步限售股解禁数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期，格式：YYYYMMDD
            float_date: 解禁日期，格式：YYYYMMDD
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步限售股解禁数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"float_date={float_date}, start_date={start_date}, end_date={end_date}")

            # 获取 Tushare 数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_share_float,
                ts_code=ts_code,
                ann_date=ann_date,
                float_date=float_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到限售股解禁数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从 Tushare 获取到 {len(df)} 条限售股解禁数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.share_float_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条限售股解禁数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            error_msg = f"同步限售股解禁数据失败: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "records": 0,
                "error": error_msg
            }

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        if df is None or df.empty:
            return df

        # 复制数据，避免修改原始 DataFrame
        df = df.copy()

        # 必需字段检查
        required_cols = ['ts_code', 'ann_date', 'float_date', 'holder_name']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        # 删除重复记录
        original_count = len(df)
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'float_date', 'holder_name'])
        if len(df) < original_count:
            logger.warning(f"删除了 {original_count - len(df)} 条重复记录")

        # 删除 NaN 值
        df = df.dropna(subset=required_cols)

        # 数据类型转换
        if 'float_share' in df.columns:
            df['float_share'] = pd.to_numeric(df['float_share'], errors='coerce')

        if 'float_ratio' in df.columns:
            df['float_ratio'] = pd.to_numeric(df['float_ratio'], errors='coerce')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")

        return df

    def _format_date(self, date_str: str) -> str:
        """
        格式化日期：YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD 格式的日期字符串

        Returns:
            YYYY-MM-DD 格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
