"""
港股通每日成交统计服务

职责：
- 处理港股通成交数据的业务逻辑
- 从 Tushare 获取数据并保存到数据库
- 提供数据查询和统计功能
"""

import asyncio
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import GgtDailyRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class GgtDailyService:
    """港股通每日成交统计服务"""

    def __init__(self):
        self.ggt_daily_repo = GgtDailyRepository()
        self.provider_factory = DataProviderFactory()

    async def sync_data(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        同步港股通成交数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            同步结果

        Examples:
            >>> service = GgtDailyService()
            >>> result = await service.sync_data(trade_date='20240315')
            >>> result = await service.sync_data(start_date='20240301', end_date='20240315')
        """
        try:
            logger.info(f"开始同步港股通成交数据: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 1. 获取 Tushare Provider
            provider = self._get_provider()

            # 2. 调用 Provider 方法获取数据
            df = await asyncio.to_thread(
                provider.get_ggt_daily,
                trade_date=trade_date,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到港股通成交数据")
                return {
                    "status": "success",
                    "message": "未获取到数据",
                    "records": 0
                }

            # 2. 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 3. 批量插入数据库
            records = await asyncio.to_thread(self.ggt_daily_repo.bulk_upsert, df)

            logger.info(f"成功同步 {records} 条港股通成交数据")

            return {
                "status": "success",
                "message": f"成功同步 {records} 条数据",
                "records": records,
                "date_range": {
                    "start": df['trade_date'].min() if not df.empty else None,
                    "end": df['trade_date'].max() if not df.empty else None
                }
            }

        except Exception as e:
            logger.error(f"同步港股通成交数据失败: {e}")
            raise

    async def get_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取港股通成交数据

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 每页记录数（默认30）
            offset: 分页偏移量

        Returns:
            数据和统计信息
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            # 并发获取数据、总数、统计信息
            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.ggt_daily_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.ggt_daily_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                ),
                asyncio.to_thread(
                    self.ggt_daily_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（便于前端显示）
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {
                "items": items,
                "total": total,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取港股通成交数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """
        获取最新港股通成交数据

        Returns:
            最新数据和统计信息

        Examples:
            >>> service = GgtDailyService()
            >>> result = await service.get_latest_data()
        """
        try:
            # 获取最新交易日期
            latest_date = await asyncio.to_thread(self.ggt_daily_repo.get_latest_trade_date)

            if not latest_date:
                return {
                    "items": [],
                    "total": 0,
                    "latest_date": None
                }

            # 获取最近30天的数据
            end_date = latest_date
            start_date_dt = datetime.strptime(latest_date, '%Y%m%d') - timedelta(days=30)
            start_date = start_date_dt.strftime('%Y%m%d')

            # 获取数据
            items = await asyncio.to_thread(
                self.ggt_daily_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                limit=30
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            # 获取统计信息
            statistics = await asyncio.to_thread(
                self.ggt_daily_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            # 格式化最新日期
            latest_date_formatted = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

            return {
                "items": items,
                "total": len(items),
                "latest_date": latest_date_formatted,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取最新港股通成交数据失败: {e}")
            raise

    # ------------------------------------------------------------------ #
    # 全量历史同步（按年切片 + Redis 续继）
    # ggt_daily 接口支持 start_date/end_date，每年约 242 条，安全低于 1000 上限
    # ------------------------------------------------------------------ #
    FULL_HISTORY_START_DATE = "20140101"
    FULL_HISTORY_PROGRESS_KEY = "sync:ggt_daily:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:ggt_daily:full_history:lock"
    FULL_HISTORY_CONCURRENCY = 3

    @staticmethod
    def _generate_years(start_date: str, end_date: str) -> list:
        """将日期范围切分为自然年片段，每片返回 (year_start, year_end)，均为 YYYYMMDD。"""
        from datetime import date
        start_y = int(start_date[:4])
        end_y = int(end_date[:4])
        end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
        segments = []
        for y in range(start_y, end_y + 1):
            ys = f"{y}0101" if y > start_y else start_date
            ye_d = min(date(y, 12, 31), end_d)
            ye = ye_d.strftime('%Y%m%d')
            segments.append((ys, ye))
        return segments

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None
    ) -> Dict:
        """
        按年切片全量同步港股通每日成交统计历史数据（支持 Redis 续继）

        每年约 242 条交易日记录，安全低于 Tushare 1000 条单次上限。
        3 并发，Redis Set 记录已完成年份起始日，支持中断续继。
        """
        effective_start = start_date or self.FULL_HISTORY_START_DATE
        today = datetime.now().strftime("%Y%m%d")
        segments = self._generate_years(effective_start, today)
        total = len(segments)
        logger.info(f"[全量ggt_daily] 共 {total} 个年段需要同步")

        completed_set = redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY)
        completed_set = {d.decode() if isinstance(d, bytes) else d for d in completed_set}
        logger.info(f"[全量ggt_daily] 已完成 {len(completed_set)} 个，剩余 {total - len(completed_set)} 个")

        pending = [(ys, ye) for ys, ye in segments if ys not in completed_set]

        provider = self._get_provider()
        success_count = 0
        skip_count = len(completed_set)
        error_count = 0
        total_records = 0

        sem = asyncio.Semaphore(self.FULL_HISTORY_CONCURRENCY)

        async def sync_year(ys: str, ye: str):
            async with sem:
                try:
                    df = await asyncio.to_thread(
                        provider.get_ggt_daily,
                        start_date=ys,
                        end_date=ye
                    )
                    records = 0
                    if df is not None and not df.empty:
                        df = self._validate_and_clean_data(df)
                        records = await asyncio.to_thread(self.ggt_daily_repo.bulk_upsert, df)
                    return ys, ye, True, records, None
                except Exception as e:
                    return ys, ye, False, 0, str(e)

        BATCH_SIZE = self.FULL_HISTORY_CONCURRENCY * 2
        for batch_start in range(0, len(pending), BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_year(ys, ye) for ys, ye in batch])

            for ys, ye, ok, records, err in results:
                if ok:
                    redis_client.sadd(self.FULL_HISTORY_PROGRESS_KEY, ys)
                    success_count += 1
                    total_records += records
                else:
                    error_count += 1
                    logger.error(f"[全量ggt_daily] {ys}~{ye} 失败（下次续继）: {err}")

            done = skip_count + success_count
            if update_state_fn:
                update_state_fn(
                    state='PROGRESS',
                    meta={
                        'current': done,
                        'total': total,
                        'percent': round(done / total * 100, 1),
                        'records': total_records,
                        'errors': error_count
                    }
                )
            logger.info(f"[全量ggt_daily] 进度: {done}/{total} ({round(done/total*100,1)}%) "
                        f"入库={total_records} 失败={error_count}")

        final_done = len(redis_client.smembers(self.FULL_HISTORY_PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(self.FULL_HISTORY_PROGRESS_KEY)
            logger.info("[全量ggt_daily] ✅ 全量同步完成，进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "records": total_records,
            "message": f"同步完成 {success_count} 个年段，入库 {total_records} 条，失败 {error_count} 个"
        }

    def _get_provider(self):
        """获取 Tushare Provider"""
        return self.provider_factory.create_provider(
            source='tushare',
            token=settings.TUSHARE_TOKEN
        )

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        验证和清洗数据

        Args:
            df: 原始数据 DataFrame

        Returns:
            清洗后的 DataFrame
        """
        if df is None or df.empty:
            return df

        # 确保必需字段存在
        required_fields = ['trade_date', 'buy_amount', 'buy_volume', 'sell_amount', 'sell_volume']
        for field in required_fields:
            if field not in df.columns:
                logger.warning(f"缺少字段: {field}")
                df[field] = None

        # 数据类型转换
        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str)

        # 数值字段转换为浮点数
        numeric_fields = ['buy_amount', 'buy_volume', 'sell_amount', 'sell_volume']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = pd.to_numeric(df[field], errors='coerce')

        # 删除重复记录（按交易日期）
        df = df.drop_duplicates(subset=['trade_date'], keep='last')

        # 按日期排序
        df = df.sort_values('trade_date')

        logger.info(f"数据验证完成，共 {len(df)} 条记录")
        return df
