"""
股东增减持Service

处理股东增减持数据的业务逻辑
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime, date
from loguru import logger
import pandas as pd

from app.repositories import StkHoldertradeRepository
from core.src.providers import DataProviderFactory


class StkHoldertradeService:
    """股东增减持服务"""

    FULL_HISTORY_START_DATE = "20090101"
    FULL_HISTORY_PROGRESS_KEY = "sync:stk_holdertrade:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:stk_holdertrade:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        self.repo = StkHoldertradeRepository()
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
        """按月切片全量同步股东增减持历史数据（支持 Redis 续继）

        stk_holdertrade 单次上限3000条，按年切片会截断，改为按月切片。
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        segments = self._generate_months(effective_start, today)
        total = len(segments)
        logger.info(f"[全量stk_holdertrade] 共 {total} 个月段需要同步")

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
                    df = await asyncio.to_thread(provider.get_stk_holdertrade, start_date=ms, end_date=me)
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.repo.bulk_upsert, df)
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
                    logger.error(f"[全量stk_holdertrade] {ms}~{me} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': done, 'total': total,
                    'percent': round(done / total * 100, 1), 'records': total_records, 'errors': error_count})
            logger.info(f"[全量stk_holdertrade] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量stk_holdertrade] ✅ 全量同步完成，进度已清除")

        return {"status": "success", "total": total, "success": success_count,
                "skipped": skip_count, "errors": error_count, "records": total_records,
                "message": f"同步完成 {success_count} 个月段，入库 {total_records} 条，失败 {error_count} 个"}

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    async def sync_stk_holdertrade(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None
    ) -> Dict:
        """
        同步股东增减持数据

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            trade_type: 交易类型 IN=增持 DE=减持
            holder_type: 股东类型 G=高管 P=个人 C=公司

        Returns:
            同步结果
        """
        try:
            logger.info(f"开始同步股东增减持数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"start_date={start_date}, end_date={end_date}, "
                       f"trade_type={trade_type}, holder_type={holder_type}")

            # 1. 获取Tushare数据
            provider = self._get_provider()
            df = await asyncio.to_thread(
                provider.get_stk_holdertrade,
                ts_code=ts_code,
                ann_date=ann_date,
                start_date=start_date,
                end_date=end_date,
                trade_type=trade_type,
                holder_type=holder_type
            )

            if df is None or df.empty:
                logger.warning("未获取到股东增减持数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条股东增减持数据")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(self.repo.bulk_upsert, df)

            logger.info(f"成功同步 {records} 条股东增减持数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步{records}条记录"
            }

        except Exception as e:
            logger.error(f"同步股东增减持数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": "同步失败"
            }

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据

        Returns:
            清洗后的数据
        """
        try:
            # 确保必需字段存在
            required_fields = [
                'ts_code', 'ann_date', 'holder_name', 'in_de'
            ]

            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 移除重复记录（基于主键）
            df = df.drop_duplicates(
                subset=['ts_code', 'ann_date', 'holder_name', 'in_de'],
                keep='last'
            )

            # 填充缺失值
            if 'holder_type' not in df.columns:
                df['holder_type'] = None

            if 'begin_date' not in df.columns:
                df['begin_date'] = None

            if 'close_date' not in df.columns:
                df['close_date'] = None

            # 数值字段填充
            numeric_fields = [
                'change_vol', 'change_ratio', 'after_share',
                'after_ratio', 'avg_price', 'total_share'
            ]

            for field in numeric_fields:
                if field not in df.columns:
                    df[field] = None

            return df

        except Exception as e:
            logger.error(f"数据验证清洗失败: {e}")
            raise

    async def get_stk_holdertrade_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        holder_type: Optional[str] = None,
        trade_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取股东增减持数据

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码
            holder_type: 股东类型
            trade_type: 交易类型
            limit: 限制数量

        Returns:
            数据字典
        """
        try:
            # 日期格式转换 YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 查询数据
            items = await asyncio.to_thread(
                self.repo.get_by_date_range,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
                holder_type=holder_type,
                trade_type=trade_type,
                limit=limit,
                offset=offset
            )

            # 日期格式转换 YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('begin_date'):
                    item['begin_date'] = self._format_date(item['begin_date'])
                if item.get('close_date'):
                    item['close_date'] = self._format_date(item['close_date'])

            # 查询统计信息和总数
            statistics, total = await asyncio.gather(
                asyncio.to_thread(
                    self.repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    holder_type=holder_type,
                    trade_type=trade_type
                )
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取股东增减持数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            ts_code: 股票代码

        Returns:
            统计信息
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            statistics = await asyncio.to_thread(
                self.repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code
            )

            return statistics

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新数据

        Returns:
            最新数据信息
        """
        try:
            latest_date = await asyncio.to_thread(self.repo.get_latest_ann_date)

            if not latest_date:
                return {
                    "latest_date": None,
                    "record_count": 0
                }

            # 格式化日期
            latest_date_formatted = self._format_date(latest_date)

            # 获取该日期的记录数
            record_count = await asyncio.to_thread(
                self.repo.get_record_count,
                start_date=latest_date,
                end_date=latest_date
            )

            return {
                "latest_date": latest_date_formatted,
                "record_count": record_count
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    @staticmethod
    def _format_date(date_str: str) -> str:
        """
        格式化日期 YYYYMMDD -> YYYY-MM-DD

        Args:
            date_str: YYYYMMDD格式的日期

        Returns:
            YYYY-MM-DD格式的日期
        """
        if not date_str or len(date_str) != 8:
            return date_str

        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
