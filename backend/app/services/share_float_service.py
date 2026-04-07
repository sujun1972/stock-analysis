"""
限售股解禁服务

处理限售股解禁数据的业务逻辑。
继承 TushareSyncBase，全量/增量同步逻辑均委托给基类。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories.share_float_repository import ShareFloatRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class ShareFloatService(TushareSyncBase):
    """限售股解禁服务"""

    TABLE_KEY = 'share_float'
    FULL_HISTORY_START_DATE = '20050101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:share_float:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:share_float:full_history:lock'
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        super().__init__()
        self.share_float_repo = ShareFloatRepository()
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
        """全量同步限售股解禁历史数据（支持 Redis 续继）

        strategy 支持：
          'by_month'   — 按自然月切片（默认）
          'by_week'    — 按 7 天窗口切片
          'by_date'    — 逐日切片
          'by_ts_code' — 逐只股票切片
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_share_float,
            upsert_fn=self.share_float_repo.bulk_upsert,
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

    async def sync_share_float(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """
        增量同步限售股解禁数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则（无 start_date 或其他策略）执行单次全量请求。

        Args:
            ts_code:       股票代码（单次请求分支使用）
            ann_date:      公告日期 YYYYMMDD（单次请求分支使用）
            float_date:    解禁日期 YYYYMMDD（单次请求分支使用）
            start_date:    时间范围起始 YYYYMMDD
            end_date:      时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（来自 sync_configs.incremental_sync_strategy）
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_share_float,
            upsert_fn=self.share_float_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='float_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
                'ann_date': ann_date,
                'float_date': float_date,
            },
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_share_float_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """获取限售股解禁数据"""
        try:
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.share_float_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    ann_date=ann_date,
                    float_date=float_date,
                    limit=limit,
                    offset=offset,
                ),
                asyncio.to_thread(
                    self.share_float_repo.get_count,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                ),
            )

            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {"items": items, "total": total}

        except Exception as e:
            logger.error(f"获取限售股解禁数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
    ) -> Dict:
        """获取限售股解禁统计信息"""
        try:
            stats = await asyncio.to_thread(
                self.share_float_repo.get_statistics,
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
            )
            stats['total_float_share_yi'] = round(stats['total_float_share'] / 100000000, 2)
            stats['avg_float_ratio_percent'] = round(stats['avg_float_ratio'] * 100, 2)
            stats['max_float_ratio_percent'] = round(stats['max_float_ratio'] * 100, 2)
            return stats

        except Exception as e:
            logger.error(f"获取限售股解禁统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict:
        """获取最新的限售股解禁数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.share_float_repo.get_latest_float_date,
                ts_code=ts_code,
            )

            if not latest_date:
                return {"latest_date": None, "items": []}

            items = await asyncio.to_thread(
                self.share_float_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=100,
            )

            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('float_date'):
                    item['float_date'] = self._format_date(item['float_date'])
                if item.get('float_share') is not None:
                    item['float_share'] = round(item['float_share'], 2)
                if item.get('float_ratio') is not None:
                    item['float_ratio'] = round(item['float_ratio'], 4)

            return {"latest_date": self._format_date(latest_date), "items": items}

        except Exception as e:
            logger.error(f"获取最新限售股解禁数据失败: {e}")
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
                f"[share_float] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）"
            )
        else:
            suggested = candidate
            logger.debug(
                f"[share_float] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）"
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

        required_cols = ['ts_code', 'ann_date', 'float_date', 'holder_name']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        original_count = len(df)
        df = df.drop_duplicates(subset=['ts_code', 'ann_date', 'float_date', 'holder_name'])
        if len(df) < original_count:
            logger.warning(f"删除了 {original_count - len(df)} 条重复记录")

        df = df.dropna(subset=required_cols)

        if 'float_share' in df.columns:
            df['float_share'] = pd.to_numeric(df['float_share'], errors='coerce')
        if 'float_ratio' in df.columns:
            df['float_ratio'] = pd.to_numeric(df['float_ratio'], errors='coerce')

        logger.info(f"数据验证完成，有效记录数: {len(df)}")
        return df

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
