"""
大宗交易服务

处理大宗交易数据的业务逻辑。
继承 TushareSyncBase，全量/增量同步逻辑均委托给基类。
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories import BlockTradeRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class BlockTradeService(TushareSyncBase):
    """大宗交易服务"""

    TABLE_KEY = 'block_trade'
    FULL_HISTORY_START_DATE = '20100101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:block_trade:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:block_trade:full_history:lock'
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        super().__init__()
        self.block_trade_repo = BlockTradeRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # ------------------------------------------------------------------
    # 全量同步
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
        """全量同步大宗交易历史数据（支持 Redis 续继）

        block_trade 单次上限1000条，按月切片避免截断。

        strategy 支持：
          'by_month'   — 按自然月切片（默认）
          'by_week'    — 按 7 天窗口切片
          'by_date'    — 逐日切片
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 1000) if cfg else 1000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_block_trade,
            upsert_fn=self.block_trade_repo.bulk_upsert,
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
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_block_trade(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """增量同步大宗交易数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则（无 start_date 或其他策略）执行单次全量请求。

        Args:
            trade_date:    交易日期 YYYYMMDD（单次请求分支使用）
            ts_code:       股票代码（单次请求分支使用）
            start_date:    时间范围起始 YYYYMMDD
            end_date:      时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（来自 sync_configs.incremental_sync_strategy）
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 1000) if cfg else 1000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_block_trade,
            upsert_fn=self.block_trade_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'trade_date': trade_date,
                'ts_code': ts_code,
            },
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_block_trade_data(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """获取大宗交易数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None

            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.block_trade_repo.get_by_date,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset,
                ),
                asyncio.to_thread(
                    self.block_trade_repo.get_count,
                    trade_date=trade_date_fmt,
                    ts_code=ts_code,
                ),
            )

            return {'items': items, 'total': total, 'count': len(items)}

        except Exception as e:
            logger.error(f"查询大宗交易数据失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取大宗交易统计数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.block_trade_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
            )
            return stats

        except Exception as e:
            logger.error(f"获取大宗交易统计数据失败: {str(e)}")
            raise

    async def get_latest_data(self) -> Dict[str, Any]:
        """获取最新大宗交易数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.block_trade_repo.get_latest_trade_date
            )

            if not latest_date:
                return {'items': [], 'latest_date': None, 'count': 0}

            items = await asyncio.to_thread(
                self.block_trade_repo.get_by_date,
                trade_date=latest_date,
                limit=100,
            )

            return {'items': items, 'latest_date': latest_date, 'count': len(items)}

        except Exception as e:
            logger.error(f"获取最新大宗交易数据失败: {str(e)}")
            raise

    async def get_suggested_start_date(self) -> Optional[str]:
        """
        计算增量同步的建议起始日期（YYYYMMDD）。

        逻辑：
          候选起始 = 今天 - incremental_default_days（从 sync_configs 读取，默认 90 天）
          上次结束 = sync_history 中最近一次增量成功的 data_end_date
          实际起始 = min(候选起始, 上次结束)，取两者中更早的，保证数据连续不遗漏
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )

        if last_end and last_end < candidate:
            suggested = last_end
            logger.debug(
                f"[block_trade] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）"
            )
        else:
            suggested = candidate
            logger.debug(
                f"[block_trade] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）"
            )

        return suggested

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        df = df.dropna(subset=required_columns)

        numeric_columns = ['price', 'vol', 'amount']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # buyer/seller 是复合主键的一部分（NOT NULL），替换空值为空字符串
        for col in ['buyer', 'seller']:
            if col in df.columns:
                df[col] = df[col].fillna('').astype(str)
                df[col] = df[col].replace('nan', '').replace('None', '')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df
