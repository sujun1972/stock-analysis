"""
股权质押统计服务

负责股权质押统计数据的同步和查询业务逻辑
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger

from app.repositories.pledge_stat_repository import PledgeStatRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class PledgeStatService(TushareSyncBase):
    """股权质押统计服务"""

    TABLE_KEY = 'pledge_stat'
    FULL_HISTORY_START_DATE = '20050101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:pledge_stat:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:pledge_stat:full_history:lock'

    def __init__(self):
        super().__init__()
        self.pledge_stat_repo = PledgeStatRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ PledgeStatService initialized")

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_ts_code',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步股权质押统计历史数据（支持 Redis 续继，策略从 sync_configs 读取）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_pledge_stat,
            upsert_fn=self.pledge_stat_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            progress_key=self.FULL_HISTORY_PROGRESS_KEY,
            strategy=strategy,
            start_date=start_date,
            full_history_start=self.FULL_HISTORY_START_DATE,
            concurrency=concurrency,
            api_limit=api_limit,
            max_requests_per_minute=max_requests_per_minute,
            update_state_fn=update_state_fn,
            table_key=self.TABLE_KEY,
        )

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """标准增量同步入口（无参数时自动从 sync_configs 读取配置）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_ts_code') if cfg else 'by_ts_code'
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        return await self.sync_pledge_stat(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_pledge_stat(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步股权质押统计数据。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        # pledge_stat 接口用 end_date，trade_date 视为 end_date
        if trade_date and not end_date:
            end_date = trade_date

        return await self.run_incremental_sync(
            fetch_fn=provider.get_pledge_stat,
            upsert_fn=self.pledge_stat_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='end_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
            },
        )

    async def get_pledge_stat_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        min_pledge_ratio: Optional[float] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """获取股权质押统计数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

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

            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {"items": items, "total": total}

        except Exception as e:
            logger.error(f"获取股权质押统计数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取统计信息"""
        try:
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
        """获取最新的股权质押统计数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.pledge_stat_repo.get_latest_end_date,
                ts_code=ts_code
            )

            if not latest_date:
                return {"items": [], "total": 0}

            items = await asyncio.to_thread(
                self.pledge_stat_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=limit
            )

            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {"items": items, "total": len(items)}

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def get_high_pledge_stocks(
        self,
        end_date: Optional[str] = None,
        min_ratio: float = 50.0,
        limit: int = 100
    ) -> Dict:
        """获取高质押比例股票"""
        try:
            if not end_date:
                latest_date = await asyncio.to_thread(
                    self.pledge_stat_repo.get_latest_end_date
                )
                if not latest_date:
                    return {"items": [], "total": 0}
                end_date_fmt = latest_date
            else:
                end_date_fmt = end_date.replace('-', '')

            items = await asyncio.to_thread(
                self.pledge_stat_repo.get_high_pledge_stocks,
                end_date=end_date_fmt,
                min_ratio=min_ratio,
                limit=limit
            )

            for item in items:
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {"items": items, "total": len(items)}

        except Exception as e:
            logger.error(f"获取高质押比例股票失败: {e}")
            raise

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        if last_end and last_end < candidate:
            return last_end
        return candidate

    def _validate_and_clean_data(self, df):
        """验证和清洗数据"""
        required_columns = ['ts_code', 'end_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        if 'end_date' in df.columns:
            df['end_date'] = df['end_date'].astype(str).str.replace('-', '')
            invalid_dates = df[df['end_date'].str.len() != 8]
            if not invalid_dates.empty:
                logger.warning(f"发现 {len(invalid_dates)} 条无效end_date记录，将被过滤")
                df = df[df['end_date'].str.len() == 8]

        df = df.drop_duplicates(subset=['ts_code', 'end_date'], keep='last')
        df['ts_code'] = df['ts_code'].fillna('')
        df['end_date'] = df['end_date'].fillna('')

        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """格式化日期用于前端显示"""
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
