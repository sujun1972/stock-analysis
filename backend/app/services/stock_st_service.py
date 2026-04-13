"""
ST股票列表服务

处理ST股票数据的同步和查询业务逻辑。
继承 TushareSyncBase，增量与全量同步逻辑委托给基类。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import pandas as pd
from loguru import logger

from app.repositories.stock_st_repository import StockStRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase


class StockStService(TushareSyncBase):
    """
    ST股票列表服务

    继承 TushareSyncBase，增量与全量同步逻辑全部委托给基类。
    """

    TABLE_KEY = 'stock_st'
    FULL_HISTORY_START_DATE = '20160101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stock_st:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:stock_st:full_history:lock'

    def __init__(self):
        super().__init__()
        self.stock_st_repo = StockStRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.info("✓ StockStService initialized")

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
        增量同步ST股票数据。

        start_date / end_date 为 YYYYMMDD。未传时通过 get_suggested_start_date 自动计算。
        sync_strategy 来自 sync_configs.incremental_sync_strategy（默认 by_month）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_month') if cfg else 'by_month'

        if start_date is None:
            start_date = await self.get_suggested_start_date()

        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stock_st,
            upsert_fn=self.stock_st_repo.bulk_upsert,
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
        concurrency: int = 1,
        strategy: str = 'by_month',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """
        全量历史同步（支持 Redis 续继）。

        strategy 默认 by_month（按月切片），与 sync_configs 配置一致。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stock_st,
            upsert_fn=self.stock_st_repo.bulk_upsert,
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

        候选起始 = 今天 - incremental_default_days（sync_configs，默认 30 天）
        上次结束 = sync_history 最近一次增量成功的 data_end_date
        实际起始 = min(候选, 上次结束)，取更早者保证数据连续
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 30) if cfg else 30

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )

        if last_end and last_end < candidate:
            logger.debug(f"[stock_st] 建议起始={last_end}（上次结束={last_end} < 候选={candidate}）")
            return last_end

        logger.debug(f"[stock_st] 建议起始={candidate}（候选={candidate}，上次结束={last_end}）")
        return candidate

    # ------------------------------------------------------------------
    # 数据清洗
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗ST股票数据"""
        try:
            required_fields = ['ts_code', 'trade_date', 'name', 'type', 'type_name']
            for field in required_fields:
                if field not in df.columns:
                    logger.warning(f"缺少字段: {field}")
                    df[field] = None

            df = df[df['ts_code'].notna() & df['trade_date'].notna()]
            df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '')
            df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')

            logger.info(f"数据清洗完成，保留 {len(df)} 条有效数据")
            return df

        except Exception as e:
            logger.error(f"数据清洗失败: {e}")
            raise

    # ------------------------------------------------------------------
    # 查询方法（保持不变）
    # ------------------------------------------------------------------

    async def get_stock_st_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        st_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict:
        """获取ST股票数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'
            offset = (page - 1) * page_size

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stock_st_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    st_type=st_type,
                    limit=page_size,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stock_st_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    st_type=st_type,
                ),
                asyncio.to_thread(
                    self.stock_st_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                ),
            )

            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "statistics": statistics
            }

        except Exception as e:
            logger.error(f"获取ST股票数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取ST股票统计信息"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            statistics = await asyncio.to_thread(
                self.stock_st_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            if statistics.get('latest_date'):
                statistics['latest_date'] = self._format_date(statistics['latest_date'])
            if statistics.get('earliest_date'):
                statistics['earliest_date'] = self._format_date(statistics['earliest_date'])

            return statistics

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_type_distribution(
        self,
        trade_date: Optional[str] = None
    ) -> List[Dict]:
        """获取ST类型分布"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            distribution = await asyncio.to_thread(
                self.stock_st_repo.get_type_distribution,
                trade_date=trade_date_fmt
            )

            return distribution

        except Exception as e:
            logger.error(f"获取ST类型分布失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """获取最新的ST股票数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.stock_st_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "trade_date": None,
                    "total": 0
                }

            items = await asyncio.to_thread(
                self.stock_st_repo.get_by_trade_date,
                trade_date=latest_date
            )

            for item in items:
                if item.get('trade_date'):
                    item['trade_date'] = self._format_date(item['trade_date'])

            return {
                "items": items,
                "trade_date": self._format_date(latest_date),
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
