"""
复权因子数据服务

继承 TushareSyncBase，增量与全量同步逻辑全部委托给基类。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from app.repositories.adj_factor_repository import AdjFactorRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase


class AdjFactorService(TushareSyncBase):
    """复权因子数据服务"""

    TABLE_KEY = 'adj_factor'
    FULL_HISTORY_START_DATE = '20210101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:adj_factor:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:adj_factor:full_history:lock'

    def __init__(self):
        super().__init__()
        self.adj_factor_repo = AdjFactorRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_incremental(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        增量同步复权因子数据。

        start_date 未传时通过 get_suggested_start_date 自动计算。
        sync_strategy 来自 sync_configs.incremental_sync_strategy。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'

        if start_date is None and trade_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_adj_factor,
            upsert_fn=self.adj_factor_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date,
            },
        )

    # ------------------------------------------------------------------
    # 全量同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 8,
        strategy: str = 'by_ts_code',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量历史复权因子同步（支持 Redis 续继）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_adj_factor,
            upsert_fn=self.adj_factor_repo.bulk_upsert,
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
            logger.debug(f"[adj_factor] 建议起始={last_end}（上次结束={last_end} < 候选={candidate}）")
            return last_end

        logger.debug(f"[adj_factor] 建议起始={candidate}（候选={candidate}，上次结束={last_end}）")
        return candidate

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_adj_factor_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        page: int = 1,
    ) -> Dict:
        """获取复权因子数据（支持分页）"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None
        offset = (page - 1) * limit

        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.adj_factor_repo.get_by_code_and_date_range,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit,
                offset=offset,
            ),
            asyncio.to_thread(
                self.adj_factor_repo.get_total_count,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
            ),
        )

        for item in items:
            if item.get('trade_date'):
                d = item['trade_date']
                item['trade_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

        return {"items": items, "total": total}

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict:
        """获取复权因子统计信息"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        stats = await asyncio.to_thread(
            self.adj_factor_repo.get_statistics,
            ts_code=ts_code,
            start_date=start_date_fmt,
            end_date=end_date_fmt,
        )

        if stats.get('latest_date'):
            d = stats['latest_date']
            stats['latest_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

        return stats

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict:
        """获取最新复权因子数据"""
        if ts_code:
            latest = await asyncio.to_thread(self.adj_factor_repo.get_latest_by_code, ts_code)
            if latest and latest.get('trade_date'):
                d = latest['trade_date']
                latest['trade_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            return latest or {}
        else:
            stats = await asyncio.to_thread(self.adj_factor_repo.get_statistics)
            if stats.get('latest_date'):
                latest_date = stats['latest_date']
                items = await asyncio.to_thread(
                    self.adj_factor_repo.get_by_code_and_date_range,
                    start_date=latest_date,
                    end_date=latest_date,
                )
                for item in items:
                    if item.get('trade_date'):
                        d = item['trade_date']
                        item['trade_date'] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                return {
                    "latest_date": f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}",
                    "items": items,
                    "total": len(items),
                }
            return {}

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗复权因子数据"""
        if df is None or df.empty:
            return df

        required_columns = ['ts_code', 'trade_date', 'adj_factor']
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            raise ValueError(f"缺少必需列: {missing}")

        original_count = len(df)
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        if len(df) < original_count:
            logger.warning(f"去除 {original_count - len(df)} 条重复记录")

        df = df.dropna(subset=['ts_code', 'trade_date'])
        df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')
        df['adj_factor'] = pd.to_numeric(df['adj_factor'], errors='coerce')
        df = df[df['adj_factor'].notna() & (df['adj_factor'] > 0)]

        logger.info(f"数据清洗完成，保留 {len(df)} 条有效记录")
        return df
