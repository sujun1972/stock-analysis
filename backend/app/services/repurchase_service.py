"""
股票回购服务

处理股票回购数据的业务逻辑。
继承 TushareSyncBase，全量/增量同步逻辑均委托给基类。
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories.repurchase_repository import RepurchaseRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class RepurchaseService(TushareSyncBase):
    """股票回购服务"""

    TABLE_KEY = 'repurchase'
    FULL_HISTORY_START_DATE = '20090101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:repurchase:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:repurchase:full_history:lock'
    FULL_HISTORY_CONCURRENCY = 5

    def __init__(self):
        super().__init__()
        self.repurchase_repo = RepurchaseRepository()
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
        """全量同步股票回购历史数据（支持 Redis 续继）

        repurchase 单次上限约1000条，按月切片避免截断。

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
            fetch_fn=provider.get_repurchase,
            upsert_fn=self.repurchase_repo.bulk_upsert,
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
        return await self.sync_repurchase(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_repurchase(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步股票回购数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则（无 start_date 或其他策略）执行单次全量请求。

        Args:
            ann_date:      公告日期 YYYYMMDD（单次请求分支使用）
            start_date:    时间范围起始 YYYYMMDD
            end_date:      时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（来自 sync_configs.incremental_sync_strategy）
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 1000) if cfg else 1000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_repurchase,
            upsert_fn=self.repurchase_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='ann_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ann_date': ann_date,
            },
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_repurchase_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        proc: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> Dict:
        """获取股票回购数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.repurchase_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    proc=proc,
                    limit=limit,
                    offset=offset,
                ),
                asyncio.to_thread(
                    self.repurchase_repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    proc=proc,
                ),
            )

            for item in items:
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('exp_date'):
                    item['exp_date'] = self._format_date(item['exp_date'])
                if item.get('amount') is not None:
                    item['amount'] = round(item['amount'] / 10000, 2)

            return {'items': items, 'total': total}

        except Exception as e:
            logger.error(f"获取股票回购数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
    ) -> Dict:
        """获取统计信息"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            statistics = await asyncio.to_thread(
                self.repurchase_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                ts_code=ts_code,
            )

            statistics['total_amount'] = round(statistics['total_amount'] / 10000, 2)
            statistics['avg_amount'] = round(statistics['avg_amount'] / 10000, 2)
            statistics['max_amount'] = round(statistics['max_amount'] / 10000, 2)
            statistics['min_amount'] = round(statistics['min_amount'] / 10000, 2)
            statistics['total_vol'] = round(statistics['total_vol'] / 10000, 2)

            return statistics

        except Exception as e:
            logger.error(f"获取回购统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Optional[Dict]:
        """获取最新回购数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.repurchase_repo.get_latest_ann_date,
                ts_code=ts_code,
            )

            if not latest_date:
                return None

            items = await asyncio.to_thread(
                self.repurchase_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                limit=1,
            )

            if items:
                item = items[0]
                if item.get('ann_date'):
                    item['ann_date'] = self._format_date(item['ann_date'])
                if item.get('end_date'):
                    item['end_date'] = self._format_date(item['end_date'])
                if item.get('exp_date'):
                    item['exp_date'] = self._format_date(item['exp_date'])
                if item.get('amount') is not None:
                    item['amount'] = round(item['amount'] / 10000, 2)
                return item

            return None

        except Exception as e:
            logger.error(f"获取最新回购数据失败: {e}")
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
                f"[repurchase] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）"
            )
        else:
            suggested = candidate
            logger.debug(
                f"[repurchase] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）"
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

        required_cols = ['ts_code', 'ann_date']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        df = df.dropna(subset=required_cols)
        df['ann_date'] = df['ann_date'].astype(str)

        for date_field in ['end_date', 'exp_date']:
            if date_field in df.columns:
                df[date_field] = df[date_field].astype(str).replace('nan', None)
                df[date_field] = df[date_field].replace('None', None)

        if 'proc' in df.columns:
            df['proc'] = df['proc'].astype(str).replace('nan', None)
            df['proc'] = df['proc'].replace('None', None)

        logger.info(f"数据清洗完成，剩余 {len(df)} 条记录")
        return df

    def _format_date(self, date_str: str) -> str:
        """格式化日期：YYYYMMDD -> YYYY-MM-DD"""
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
