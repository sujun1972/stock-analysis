"""
券商每月荐股服务

负责券商荐股数据的同步和查询业务逻辑。
继承 TushareSyncBase，_get_provider 使用基类版本（支持 rpm 限速缓存）。
注意：broker_recommend 接口只接受 month（YYYYMM），不支持日期范围，
      全量同步使用自定义月份迭代，不能使用 run_full_sync。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.broker_recommend_repository import BrokerRecommendRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class BrokerRecommendService(TushareSyncBase):
    """券商每月荐股服务"""

    TABLE_KEY = 'broker_recommend'
    FULL_HISTORY_PROGRESS_KEY = 'sync:broker_recommend:full_history:progress'

    def __init__(self):
        super().__init__()
        self.broker_repo = BrokerRecommendRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_broker_recommend(
        self,
        month: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """同步券商荐股数据（按月请求）。

        Args:
            month: 月度，格式：YYYYMM（可选，不传则同步当前月）
            max_requests_per_minute: 限速（None=继承全局）
        """
        try:
            if not month:
                month = datetime.now().strftime('%Y%m')
                logger.info(f"未指定月度，默认同步当前月: {month}")

            logger.info(f"开始同步券商荐股数据: month={month}")

            provider = self._get_provider(max_requests_per_minute)
            df = await asyncio.to_thread(
                provider.get_broker_recommend,
                month=month
            )

            if df is None or df.empty:
                logger.warning(f"未获取到券商荐股数据: month={month}")
                return {"status": "success", "records": 0, "message": "无可用数据"}

            logger.info(f"从Tushare获取到 {len(df)} 条券商荐股数据")

            df = self._validate_and_clean_data(df)

            records = await asyncio.to_thread(self.broker_repo.bulk_upsert, df)

            logger.info(f"券商荐股数据同步成功: {records} 条")
            return {"status": "success", "records": records, "month": month}

        except Exception as e:
            logger.error(f"同步券商荐股数据失败: {e}")
            return {"status": "error", "error": str(e), "records": 0}

    # ------------------------------------------------------------------
    # 全量历史同步（特殊：逐月 YYYYMM 迭代，不能用 run_full_sync）
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_month_str',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步历史数据（逐月请求，Redis Set 续继）

        broker_recommend 接口只接受 YYYYMM 格式的 month 参数，
        不支持日期范围查询，因此必须手动迭代每个月份。
        """
        from datetime import date as date_cls

        PROGRESS_KEY = self.FULL_HISTORY_PROGRESS_KEY

        if start_date and len(start_date) >= 6:
            start_year, start_month = int(start_date[:4]), int(start_date[4:6])
        else:
            start_year, start_month = 2018, 1

        today = date_cls.today()
        months = []
        y, m = start_year, start_month
        while (y, m) <= (today.year, today.month):
            months.append(f"{y:04d}{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1

        completed = {v.decode() if isinstance(v, bytes) else v
                     for v in (redis_client.smembers(PROGRESS_KEY) if redis_client else set())}
        pending = [mo for mo in months if mo not in completed]

        total_records = 0
        total_months = len(months)
        done_months = total_months - len(pending)

        sem = asyncio.Semaphore(max(1, concurrency))

        async def sync_month(month_str):
            nonlocal total_records, done_months
            async with sem:
                result = await self.sync_broker_recommend(
                    month=month_str,
                    max_requests_per_minute=max_requests_per_minute or None
                )
                if result.get('status') != 'error':
                    if redis_client:
                        redis_client.sadd(PROGRESS_KEY, month_str)
                done_months += 1
                total_records += result.get('records', 0)
                if update_state_fn:
                    update_state_fn(state='PROGRESS', meta={
                        'done': done_months,
                        'total': total_months,
                        'records': total_records,
                    })

        BATCH_SIZE = 10
        for i in range(0, len(pending), BATCH_SIZE):
            batch = pending[i:i + BATCH_SIZE]
            await asyncio.gather(*[sync_month(mo) for mo in batch])

        # 全量同步正常完成后清理 progress key，下次可重新全量同步
        if redis_client and done_months >= total_months:
            redis_client.delete(PROGRESS_KEY)

        return {
            'status': 'success',
            'records': total_records,
            'done': done_months,
            'total': total_months,
        }

    # ------------------------------------------------------------------
    # 建议起始日期
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始月度（YYYYMM）。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 30) if cfg else 30
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        if last_end and last_end < candidate:
            return last_end
        return candidate

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df):
        """验证和清洗数据"""
        try:
            required_columns = ['month', 'broker', 'ts_code']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"缺少必需列: {col}")

            df = df.dropna(subset=required_columns)

            if 'name' not in df.columns:
                df['name'] = None

            df = df.drop_duplicates(subset=['month', 'broker', 'ts_code'])

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_broker_recommend_data(
        self,
        month: Optional[str] = None,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        broker: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """查询券商荐股数据"""
        try:
            effective_start = start_month
            effective_end = end_month
            if not month and not start_month and not end_month:
                effective_end = datetime.now().strftime('%Y%m')
                effective_start = (datetime.now() - timedelta(days=90)).strftime('%Y%m')
                logger.info(f"未指定日期，默认查询最近3个月: {effective_start} ~ {effective_end}")
            elif not start_month:
                effective_start = '190001'
            elif not end_month:
                effective_end = '299912'

            if month:
                items_coro = asyncio.to_thread(
                    self.broker_repo.get_by_month, month, broker, limit
                )
                stats_coro = asyncio.to_thread(
                    self.broker_repo.get_statistics, month, month
                )
            else:
                items_coro = asyncio.to_thread(
                    self.broker_repo.get_by_month_range,
                    effective_start, effective_end, broker, ts_code, limit, offset
                )
                stats_coro = asyncio.to_thread(
                    self.broker_repo.get_statistics, effective_start, effective_end
                )

            items, statistics = await asyncio.gather(items_coro, stats_coro)

            return {
                "items": items,
                "statistics": statistics,
                "total": statistics.get('total_records', len(items))
            }

        except Exception as e:
            logger.error(f"查询券商荐股数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> Dict:
        """获取统计信息"""
        try:
            return await asyncio.to_thread(
                self.broker_repo.get_statistics, start_month, end_month
            )
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_month(self) -> Optional[str]:
        """获取最新月度"""
        try:
            return await asyncio.to_thread(self.broker_repo.get_latest_month)
        except Exception as e:
            logger.error(f"获取最新月度失败: {e}")
            raise

    async def get_broker_list(self, month: Optional[str] = None) -> list:
        """获取券商列表"""
        try:
            return await asyncio.to_thread(self.broker_repo.get_broker_list, month)
        except Exception as e:
            logger.error(f"获取券商列表失败: {e}")
            raise

    async def get_top_stocks(self, month: str, limit: int = 20) -> list:
        """获取某月被推荐次数最多的股票"""
        try:
            return await asyncio.to_thread(self.broker_repo.get_top_stocks, month, limit)
        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            raise
