"""
AH股比价数据同步服务

负责从 Tushare 获取 AH股比价数据并同步到数据库。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import StkAhComparisonRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class StkAhComparisonService(TushareSyncBase):
    """AH股比价数据同步服务"""

    TABLE_KEY = 'stk_ah_comparison'
    FULL_HISTORY_START_DATE = '20250812'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_ah_comparison:full_history:progress'

    def __init__(self):
        super().__init__()
        self.stk_ah_comparison_repo = StkAhComparisonRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 增量同步（标准入口）
    # ------------------------------------------------------------------

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
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        return await self.sync_stk_ah_comparison(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_stk_ah_comparison(
        self,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步AH股比价数据。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_ah_comparison,
            upsert_fn=self.stk_ah_comparison_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'hk_code': hk_code,
                'ts_code': ts_code,
                'trade_date': trade_date,
            },
        )

    # ------------------------------------------------------------------
    # 全量历史同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_month',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步历史数据（按月切片，Redis Set 续继）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_ah_comparison,
            upsert_fn=self.stk_ah_comparison_repo.bulk_upsert,
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

    # ------------------------------------------------------------------
    # 建议起始日期
    # ------------------------------------------------------------------

    async def get_suggested_start_date(self) -> Optional[str]:
        """计算增量同步的建议起始日期（YYYYMMDD）。"""
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
        required_fields = ['hk_code', 'ts_code', 'trade_date']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        df = df.dropna(subset=['trade_date'])

        numeric_fields = ['hk_pct_chg', 'hk_close', 'close', 'pct_chg', 'ah_comparison', 'ah_premium']
        for field in numeric_fields:
            if field in df.columns:
                df[field] = df[field].astype(float, errors='ignore')

        logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
        return df

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.stk_ah_comparison_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.stk_ah_comparison_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_stk_ah_comparison_data(
        self,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """查询AH股比价数据"""
        items, total, statistics = await asyncio.gather(
            asyncio.to_thread(
                self.stk_ah_comparison_repo.get_by_date_range,
                start_date=start_date,
                end_date=end_date,
                hk_code=hk_code,
                ts_code=ts_code,
                limit=limit,
                offset=offset
            ),
            asyncio.to_thread(
                self.stk_ah_comparison_repo.get_record_count,
                start_date=start_date,
                end_date=end_date
            ),
            asyncio.to_thread(
                self.stk_ah_comparison_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )
        )

        return {"items": items, "statistics": statistics, "total": total}

    async def get_top_premium(self, trade_date: Optional[str] = None, limit: int = 20) -> Dict:
        """获取溢价率最高的股票"""
        items = await asyncio.to_thread(
            self.stk_ah_comparison_repo.get_top_premium,
            trade_date=trade_date,
            limit=limit
        )
        return {"items": items, "total": len(items)}

    async def get_latest_trade_date(self) -> Optional[str]:
        """获取最新交易日期"""
        return await asyncio.to_thread(self.stk_ah_comparison_repo.get_latest_trade_date)
