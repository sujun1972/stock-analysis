"""
每日筹码及胜率数据服务

处理筹码及胜率数据的业务逻辑。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.cyq_perf_repository import CyqPerfRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class CyqPerfService(TushareSyncBase):
    """每日筹码及胜率数据服务"""

    TABLE_KEY = 'cyq_perf'
    FULL_HISTORY_START_DATE = '20180101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:cyq_perf:full_history:progress'

    def __init__(self):
        super().__init__()
        self.cyq_perf_repo = CyqPerfRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ CyqPerfService initialized")

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
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_ts_code') if cfg else 'by_ts_code'
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        return await self.sync_cyq_perf(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_cyq_perf(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步筹码及胜率数据。

        cyq_perf 接口要求 ts_code 或 trade_date 至少传一个，
        支持 by_ts_code（逐只股票）和 by_date（按 trade_date 逐日切片）策略。
        """
        if sync_strategy and sync_strategy not in ('by_ts_code', 'by_date', 'none'):
            logger.warning(
                f"[cyq_perf] 不支持 sync_strategy={sync_strategy}，强制使用 by_ts_code"
            )
            sync_strategy = 'by_ts_code'

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_cyq_perf,
            upsert_fn=self.cyq_perf_repo.bulk_upsert,
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
            date_param='trade_date' if sync_strategy == 'by_date' else None,
        )

    # ------------------------------------------------------------------
    # 全量历史同步
    # ------------------------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_ts_code',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步历史数据（逐只股票请求，Redis Set 续继）

        cyq_perf 接口服务端要求 ts_code 或 trade_date 至少传一个，
        不支持纯按日期范围全市场查询，只能使用 by_ts_code 策略。
        """
        if strategy != 'by_ts_code':
            logger.warning(
                f"[cyq_perf] 接口不支持按日期范围全市场查询，"
                f"忽略 strategy={strategy}，强制使用 by_ts_code"
            )
            strategy = 'by_ts_code'

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_cyq_perf,
            upsert_fn=self.cyq_perf_repo.bulk_upsert,
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
        try:
            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            df = df.dropna(subset=required_fields)

            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str)

            numeric_fields = [
                'his_low', 'his_high',
                'cost_5pct', 'cost_15pct', 'cost_50pct', 'cost_85pct', 'cost_95pct',
                'weight_avg', 'winner_rate'
            ]
            for field in numeric_fields:
                if field in df.columns:
                    df[field] = df[field].apply(lambda x: None if str(x).strip() in ('', 'nan', 'None') else x)

            logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        latest = await asyncio.to_thread(self.cyq_perf_repo.get_latest_trade_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_cyq_perf_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """查询筹码及胜率数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.cyq_perf_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.cyq_perf_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.cyq_perf_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            return {"items": items, "statistics": statistics, "total": total}

        except Exception as e:
            logger.error(f"获取筹码及胜率数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """获取最新的筹码及胜率数据"""
        try:
            latest_date = await asyncio.to_thread(self.cyq_perf_repo.get_latest_trade_date)
            if not latest_date:
                return {"latest_date": None, "data": []}
            items = await asyncio.to_thread(
                self.cyq_perf_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                page_size=100
            )
            return {"latest_date": latest_date, "data": items}
        except Exception as e:
            logger.error(f"获取最新筹码及胜率数据失败: {e}")
            raise

    async def get_top_winner_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取高胜率股票"""
        try:
            if not trade_date:
                latest_date = await asyncio.to_thread(self.cyq_perf_repo.get_latest_trade_date)
                if not latest_date:
                    return []
                trade_date_fmt = latest_date
            else:
                trade_date_fmt = trade_date.replace('-', '')

            return await asyncio.to_thread(
                self.cyq_perf_repo.get_top_winner_stocks,
                trade_date=trade_date_fmt,
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取高胜率股票失败: {e}")
            raise
