"""
股东增减持服务

处理股东增减持数据的业务逻辑。
继承 TushareSyncBase，全量/增量同步逻辑均委托给基类。
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories import StkHoldertradeRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class StkHoldertradeService(TushareSyncBase):
    """股东增减持服务"""

    TABLE_KEY = 'stk_holdertrade'
    FULL_HISTORY_START_DATE = '20090101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_holdertrade:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:stk_holdertrade:full_history:lock'
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        super().__init__()
        self.repo = StkHoldertradeRepository()
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
        """全量同步股东增减持历史数据（支持 Redis 续继）

        stk_holdertrade 单次上限约3000条，按月切片避免截断。

        strategy 支持：
          'by_month'   — 按自然月切片（默认）
          'by_week'    — 按 7 天窗口切片
          'by_date'    — 逐日切片
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_holdertrade,
            upsert_fn=self.repo.bulk_upsert,
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
        return await self.sync_stk_holdertrade(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_stk_holdertrade(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步股东增减持数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则（无 start_date 或其他策略）执行单次全量请求。

        Args:
            ts_code:       股票代码（单次请求分支使用）
            ann_date:      公告日期 YYYYMMDD（单次请求分支使用）
            trade_type:    交易类型（单次请求分支使用）
            holder_type:   股东类型（单次请求分支使用）
            start_date:    时间范围起始 YYYYMMDD
            end_date:      时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（来自 sync_configs.incremental_sync_strategy）
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_holdertrade,
            upsert_fn=self.repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='ann_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date,
                'trade_type': trade_type,
                'holder_type': holder_type,
            },
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_stk_holdertrade_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        holder_type: Optional[str] = None,
        trade_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """获取股东增减持数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            items, statistics, total = await asyncio.gather(
                asyncio.to_thread(
                    self.repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    holder_type=holder_type,
                    trade_type=trade_type,
                    limit=limit,
                    offset=offset,
                ),
                asyncio.to_thread(
                    self.repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                ),
                asyncio.to_thread(
                    self.repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    holder_type=holder_type,
                    trade_type=trade_type,
                ),
            )

            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('begin_date'):
                    item['begin_date'] = self._format_date(item['begin_date'])
                if item.get('close_date'):
                    item['close_date'] = self._format_date(item['close_date'])

            return {'items': items, 'statistics': statistics, 'total': total}

        except Exception as e:
            logger.error(f"获取股东增减持数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
    ) -> Dict:
        """获取统计信息"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            return await asyncio.to_thread(
                self.repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
            )

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """获取最新数据"""
        try:
            latest_date = await asyncio.to_thread(self.repo.get_latest_ann_date)

            if not latest_date:
                return {'latest_date': None, 'record_count': 0}

            record_count = await asyncio.to_thread(
                self.repo.get_record_count,
                start_date=latest_date,
                end_date=latest_date,
            )

            return {
                'latest_date': self._format_date(latest_date),
                'record_count': record_count,
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
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
                f"[stk_holdertrade] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）"
            )
        else:
            suggested = candidate
            logger.debug(
                f"[stk_holdertrade] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）"
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

        required_fields = ['ts_code', 'ann_date', 'holder_name', 'in_de']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        df = df.drop_duplicates(
            subset=['ts_code', 'ann_date', 'holder_name', 'in_de'],
            keep='last',
        )

        for col in ['holder_type', 'begin_date', 'close_date']:
            if col not in df.columns:
                df[col] = None

        for field in ['change_vol', 'change_ratio', 'after_share', 'after_ratio', 'avg_price', 'total_share']:
            if field not in df.columns:
                df[field] = None

        return df

    @staticmethod
    def _format_date(date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
