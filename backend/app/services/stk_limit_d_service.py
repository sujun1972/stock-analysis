"""
每日涨跌停价格服务

管理每日涨跌停价格数据的同步和查询。
继承 TushareSyncBase，增量与全量同步逻辑委托给基类。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import pandas as pd
from loguru import logger

from app.repositories.stk_limit_d_repository import StkLimitDRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase


class StkLimitDService(TushareSyncBase):
    """
    每日涨跌停价格服务

    继承 TushareSyncBase，增量与全量同步逻辑全部委托给基类。
    """

    TABLE_KEY = 'stk_limit_d'
    FULL_HISTORY_START_DATE = '20210101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_limit_d:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:stk_limit_d:full_history:lock'

    def __init__(self):
        super().__init__()
        self.stk_limit_d_repo = StkLimitDRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ StkLimitDService initialized")

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        增量同步每日涨跌停价格数据。

        start_date / end_date 为 YYYYMMDD。未传时通过 get_suggested_start_date 自动计算。
        sync_strategy 来自 sync_configs.incremental_sync_strategy（默认 by_date_range）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'

        if start_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_limit_d,
            upsert_fn=self.stk_limit_d_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
        )

    # ------------------------------------------------------------------
    # 全量同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 3,
        strategy: str = 'by_ts_code',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """
        全量历史同步（支持 Redis 续继）。

        strategy 默认 by_ts_code（逐只股票拉取），与 sync_configs 配置一致。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_limit_d,
            upsert_fn=self.stk_limit_d_repo.bulk_upsert,
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
        """
        计算增量同步建议起始日期（YYYYMMDD）。

        候选起始 = 今天 - incremental_default_days（sync_configs，默认 7 天）
        上次结束 = sync_history 最近一次增量成功的 data_end_date
        实际起始 = min(候选, 上次结束)，取更早者保证数据连续
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )

        if last_end and last_end < candidate:
            logger.debug(f"[stk_limit_d] 建议起始={last_end}（上次结束={last_end} < 候选={candidate}）")
            return last_end

        logger.debug(f"[stk_limit_d] 建议起始={candidate}（候选={candidate}，上次结束={last_end}）")
        return candidate

    # ------------------------------------------------------------------
    # 数据清洗
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据验证和清洗"""
        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        df = df.dropna(subset=['trade_date', 'ts_code'])

        if 'trade_date' in df.columns:
            df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")
        return df

    # ------------------------------------------------------------------
    # 查询方法（保持不变）
    # ------------------------------------------------------------------

    async def get_stk_limit_d_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """获取每日涨跌停价格数据（支持分页）"""
        try:
            if not start_date and not end_date:
                end_date_dt = datetime.now()
                start_date_dt = end_date_dt - timedelta(days=30)
                start_date = start_date_dt.strftime('%Y%m%d')
                end_date = end_date_dt.strftime('%Y%m%d')

            effective_start = start_date or '19900101'
            effective_end = end_date or '29991231'
            offset = (page - 1) * page_size

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_by_date_range,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_total_count,
                    start_date=effective_start,
                    end_date=effective_end,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.stk_limit_d_repo.get_statistics,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                )
            )

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取每日涨跌停价格数据失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 100) -> Dict[str, Any]:
        """获取最新的每日涨跌停价格数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.stk_limit_d_repo.get_latest_trade_date
            )

            if not latest_date:
                return {"items": [], "latest_date": None, "total": 0}

            items = await asyncio.to_thread(
                self.stk_limit_d_repo.get_by_trade_date,
                trade_date=latest_date
            )

            items = items[:limit] if items else []

            return {
                "items": items,
                "latest_date": latest_date,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新每日涨跌停价格数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            statistics = await asyncio.to_thread(
                self.stk_limit_d_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code
            )
            return statistics

        except Exception as e:
            logger.error(f"获取每日涨跌停价格统计信息失败: {e}")
            raise
