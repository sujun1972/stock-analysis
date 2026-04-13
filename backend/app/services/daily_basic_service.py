"""
每日指标服务

提供每日指标数据（换手率、市盈率、市净率等）的同步和查询功能。
继承 TushareSyncBase，增量与全量同步逻辑委托给基类。
数据来源：Tushare Pro daily_basic 接口
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import pandas as pd
from loguru import logger

from app.repositories import DailyBasicRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.services.tushare_sync_base import TushareSyncBase


class DailyBasicService(TushareSyncBase):
    """
    每日指标服务

    继承 TushareSyncBase，增量与全量同步逻辑全部委托给基类。
    """

    TABLE_KEY = 'daily_basic'
    FULL_HISTORY_START_DATE = '20210101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:daily_basic:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:daily_basic:full_history:lock'

    def __init__(self):
        super().__init__()
        self.daily_basic_repo = DailyBasicRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.info("✓ DailyBasicService initialized")

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
        增量同步每日指标数据。

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
            fetch_fn=provider.get_daily_basic,
            upsert_fn=self.daily_basic_repo.bulk_upsert,
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
        concurrency: int = 8,
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
            fetch_fn=provider.get_daily_basic,
            upsert_fn=self.daily_basic_repo.bulk_upsert,
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
            logger.debug(f"[daily_basic] 建议起始={last_end}（上次结束={last_end} < 候选={candidate}）")
            return last_end

        logger.debug(f"[daily_basic] 建议起始={candidate}（候选={candidate}，上次结束={last_end}）")
        return candidate

    # ------------------------------------------------------------------
    # 数据清洗
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗每日指标数据"""
        df = df.dropna(subset=['trade_date', 'ts_code'])

        required_columns = ['trade_date', 'ts_code']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需字段: {col}")

        numeric_columns = [
            'close', 'turnover_rate', 'turnover_rate_f', 'volume_ratio',
            'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm',
            'dv_ratio', 'dv_ttm', 'total_share', 'float_share',
            'free_share', 'total_mv', 'circ_mv'
        ]
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        logger.info(f"数据清洗完成，有效数据 {len(df)} 条")
        return df

    # ------------------------------------------------------------------
    # 查询方法（保持不变）
    # ------------------------------------------------------------------

    async def get_daily_basic_data(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """查询每日指标数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            items = await asyncio.to_thread(
                self.daily_basic_repo.get_by_code_and_date_range,
                ts_code=ts_code,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                limit=limit
            )

            return {
                "items": items,
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"查询每日指标数据失败: {str(e)}")
            raise

    async def get_daily_basic_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict[str, Any]:
        """查询每日指标数据列表（支持分页）"""
        try:
            offset = (page - 1) * page_size

            if trade_date:
                items = await asyncio.to_thread(
                    self.daily_basic_repo.get_by_date_range,
                    start_date=trade_date,
                    end_date=trade_date,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                )
                total = await asyncio.to_thread(
                    self.daily_basic_repo.get_record_count,
                    start_date=trade_date,
                    end_date=trade_date
                )
            else:
                if not start_date:
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                if not end_date:
                    end_date = datetime.now().strftime('%Y%m%d')

                items = await asyncio.to_thread(
                    self.daily_basic_repo.get_by_date_range,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code,
                    limit=page_size,
                    offset=offset
                )
                total = await asyncio.to_thread(
                    self.daily_basic_repo.get_record_count,
                    start_date=start_date,
                    end_date=end_date
                )

            for item in items:
                if 'trade_date' in item and item['trade_date']:
                    date_obj = item['trade_date']
                    if hasattr(date_obj, 'strftime'):
                        item['trade_date'] = date_obj.strftime('%Y-%m-%d')
                    else:
                        item['trade_date'] = f"{str(date_obj)[:4]}-{str(date_obj)[4:6]}-{str(date_obj)[6:8]}"

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size
            }

        except Exception as e:
            logger.error(f"查询每日指标数据列表失败: {str(e)}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取每日指标统计数据"""
        try:
            stats = await asyncio.to_thread(
                self.daily_basic_repo.get_statistics,
                start_date=start_date,
                end_date=end_date
            )

            if stats.get('date_range'):
                earliest = stats['date_range'].get('earliest_date', '')
                latest = stats['date_range'].get('latest_date', '')

                if earliest and len(earliest) == 8 and earliest.isdigit():
                    stats['date_range']['earliest_date'] = f"{earliest[:4]}-{earliest[4:6]}-{earliest[6:8]}"
                if latest and len(latest) == 8 and latest.isdigit():
                    stats['date_range']['latest_date'] = f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"

            if stats.get('avg_pe_ttm') is None:
                stats['avg_pe_ttm'] = 0.0

            return stats

        except Exception as e:
            logger.error(f"获取每日指标统计数据失败: {str(e)}")
            raise

    async def get_latest_data(self) -> Dict[str, Any]:
        """获取最新交易日的每日指标数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.daily_basic_repo.get_latest_trade_date
            )

            if not latest_date:
                return {
                    "items": [],
                    "trade_date": None
                }

            items = await asyncio.to_thread(
                self.daily_basic_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=100
            )

            for item in items:
                if 'trade_date' in item and item['trade_date']:
                    date_str = item['trade_date']
                    if hasattr(date_str, 'strftime'):
                        date_str = date_str.strftime('%Y%m%d')
                    if isinstance(date_str, str) and len(date_str) == 8 and date_str.isdigit():
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {
                "items": items,
                "trade_date": latest_date,
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新每日指标数据失败: {str(e)}")
            raise
