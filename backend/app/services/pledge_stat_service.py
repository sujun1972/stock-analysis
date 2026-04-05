"""
股权质押统计服务

负责股权质押统计数据的同步和查询业务逻辑
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.pledge_stat_repository import PledgeStatRepository
from core.src.providers import DataProviderFactory


class PledgeStatService:
    """股权质押统计服务"""

    FULL_HISTORY_PROGRESS_KEY = "sync:pledge_stat:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:pledge_stat:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        self.pledge_stat_repo = PledgeStatRepository()
        self.provider_factory = DataProviderFactory()
        logger.debug("✓ PledgeStatService initialized")

    async def sync_full_history(self, redis_client, start_date: Optional[str] = None, update_state_fn=None) -> Dict:
        """逐只股票全量同步股权质押统计历史数据（支持 Redis 续继）

        pledge_stat 接口只支持 ts_code + end_date，无法按日期范围拉全市场，
        需逐只股票请求（不传 end_date 则返回该股全量历史记录）。
        """
        from app.repositories.stock_basic_repository import StockBasicRepository

        all_ts_codes = await asyncio.to_thread(
            StockBasicRepository().get_listed_ts_codes, status='L'
        )
        total = len(all_ts_codes)
        logger.info(f"[全量pledge_stat] 共 {total} 只股票需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        pending = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        success_count = 0
        error_count = 0
        total_records = 0

        provider = self._get_provider()
        sem = asyncio.Semaphore(self.FULL_HISTORY_CONCURRENCY)

        async def sync_one(ts_code: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(provider.get_pledge_stat, ts_code=ts_code)
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.pledge_stat_repo.bulk_upsert, df)
                    return ts_code, True, records, None
                except Exception as e:
                    return ts_code, False, 0, str(e)

        BATCH_SIZE = 50
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_one(c) for c in batch])
            for ts_code, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ts_code)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量pledge_stat] {ts_code} 失败（下次续继）: {err}")
            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(state='PROGRESS', meta={'current': done, 'total': total,
                    'percent': round(done / total * 100, 1), 'records': total_records, 'errors': error_count})
            logger.info(f"[全量pledge_stat] 进度: {done}/{total} ({round(done/total*100,1)}%) 入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量pledge_stat] ✅ 全量同步完成，进度已清除")

        return {"status": "success", "total": total, "success": success_count,
                "skipped": skip_count, "errors": error_count, "records": total_records,
                "message": f"同步完成 {success_count} 只股票，入库 {total_records} 条，失败 {error_count} 只"}

    async def sync_pledge_stat(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        同步股权质押统计数据

        Args:
            trade_date: 单个交易日期 YYYYMMDD (实际为end_date)
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            同步结果字典
        """
        try:
            logger.info(f"开始同步股权质押统计数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, ts_code={ts_code}")

            # 1. 获取Tushare数据
            provider = self._get_provider()

            # Tushare pledge_stat接口使用end_date参数
            # 如果提供了trade_date，使用它作为end_date
            if trade_date:
                end_date = trade_date

            df = await asyncio.to_thread(
                provider.get_pledge_stat,
                ts_code=ts_code,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"从Tushare获取到 {len(df)} 条记录")

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(
                self.pledge_stat_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条股权质押统计记录")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条记录"
            }

        except Exception as e:
            logger.error(f"同步股权质押统计数据失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "error": str(e),
                "message": f"同步失败: {str(e)}"
            }

    async def get_pledge_stat_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        min_pledge_ratio: Optional[float] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取股权质押统计数据

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            ts_code: 股票代码（可选）
            min_pledge_ratio: 最小质押比例（可选）
            limit: 返回记录数限制

        Returns:
            数据字典，包含items和total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取数据
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.pledge_stat_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    min_pledge_ratio=min_pledge_ratio,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.pledge_stat_repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取股权质押统计数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.pledge_stat_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None, limit: int = 20) -> Dict:
        """
        获取最新的股权质押统计数据

        Args:
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 获取最新截止日期
            latest_date = await asyncio.to_thread(
                self.pledge_stat_repo.get_latest_end_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {"items": [], "total": 0}

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.pledge_stat_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def get_high_pledge_stocks(
        self,
        end_date: Optional[str] = None,
        min_ratio: float = 50.0,
        limit: int = 100
    ) -> Dict:
        """
        获取高质押比例股票

        Args:
            end_date: 截止日期（YYYY-MM-DD格式），默认为最新日期
            min_ratio: 最小质押比例（默认50%）
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 如果未提供日期，使用最新日期
            if not end_date:
                latest_date = await asyncio.to_thread(
                    self.pledge_stat_repo.get_latest_end_date
                )
                if not latest_date:
                    return {"items": [], "total": 0}
                end_date_fmt = latest_date
            else:
                # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
                end_date_fmt = end_date.replace('-', '')

            # 获取高质押比例股票
            items = await asyncio.to_thread(
                self.pledge_stat_repo.get_high_pledge_stocks,
                end_date=end_date_fmt,
                min_ratio=min_ratio,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取高质押比例股票失败: {e}")
            raise

    def _get_provider(self):
        """获取Tushare数据提供者"""
        from app.core.config import settings
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需列存在
        required_columns = ['ts_code', 'end_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 确保日期格式为 YYYYMMDD（8位）
        if 'end_date' in df.columns:
            df['end_date'] = df['end_date'].astype(str).str.replace('-', '')
            # 验证日期格式
            invalid_dates = df[df['end_date'].str.len() != 8]
            if not invalid_dates.empty:
                logger.warning(f"发现 {len(invalid_dates)} 条无效end_date记录，将被过滤")
                df = df[df['end_date'].str.len() == 8]

        # 删除重复记录
        df = df.drop_duplicates(subset=['ts_code', 'end_date'], keep='last')

        # 处理空值 - 数值类型保持None
        # 只为必需字段提供默认值
        df['ts_code'] = df['ts_code'].fillna('')
        df['end_date'] = df['end_date'].fillna('')

        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于前端显示

        Args:
            date_str: YYYYMMDD格式的日期字符串

        Returns:
            YYYY-MM-DD格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
