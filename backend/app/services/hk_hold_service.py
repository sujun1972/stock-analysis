"""
北向资金持股服务

提供北向资金持股数据（沪股通、深股通）的同步和查询功能。
继承 TushareSyncBase，同步逻辑委托给基类。
数据来源：Tushare Pro hk_hold 接口
积分消耗：2000分/次
注意：该接口仅支持到2025年，2026年及以后请使用 moneyflow_hsgt 接口
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import HkHoldRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class HkHoldService(TushareSyncBase):
    """北向资金持股服务"""

    TABLE_KEY = 'hk_hold'
    FULL_HISTORY_START_DATE = '20170301'
    FULL_HISTORY_PROGRESS_KEY = 'sync:hk_hold:full_history:progress'

    def __init__(self):
        super().__init__()
        self.hk_hold_repo = HkHoldRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_hk_hold(
        self,
        code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """增量同步北向资金持股数据。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_hk_hold,
            upsert_fn=self.hk_hold_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'code': code,
                'ts_code': ts_code,
                'trade_date': trade_date,
                'exchange': exchange,
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
    ) -> Dict[str, Any]:
        """全量同步历史数据（按月切片，Redis Set 续继）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_hk_hold,
            upsert_fn=self.hk_hold_repo.bulk_upsert,
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
        import pandas as pd
        df = df.dropna(subset=['trade_date', 'ts_code'])

        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        numeric_columns = ['vol', 'ratio', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
        return df

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.hk_hold_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.hk_hold_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_hk_hold_data(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        code: Optional[str] = None,
        exchange: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """查询北向资金持股数据（支持分页和排序）"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.hk_hold_repo.get_paged,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    page=page,
                    page_size=page_size
                ),
                asyncio.to_thread(
                    self.hk_hold_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange
                ),
                asyncio.to_thread(
                    self.hk_hold_repo.get_statistics_by_date,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    code=code,
                    exchange=exchange
                )
            )

            return {"items": items, "total": total, "statistics": statistics}

        except Exception as e:
            logger.error(f"查询北向资金持股数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取北向资金持股统计数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            return await asyncio.to_thread(
                self.hk_hold_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )
        except Exception as e:
            logger.error(f"获取北向资金持股统计数据失败: {str(e)}")
            raise
