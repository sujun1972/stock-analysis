"""
神奇九转指标数据服务

处理神奇九转指标数据的业务逻辑。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

from typing import Optional, Dict, List
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from app.repositories import StkNineturnRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.stock_quote_cache import stock_quote_cache
from app.services.tushare_sync_base import TushareSyncBase


class StkNineturnService(TushareSyncBase):
    """神奇九转指标数据服务"""

    TABLE_KEY = 'stk_nineturn'
    FULL_HISTORY_START_DATE = '20230101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_nineturn:full_history:progress'

    def __init__(self):
        super().__init__()
        self.stk_nineturn_repo = StkNineturnRepository()
        self.sync_history_repo = SyncHistoryRepository()

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
        return await self.sync_stk_nineturn(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_stk_nineturn(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        freq: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步神奇九转指标数据。

        stk_nineturn 接口要求 ts_code 或日期至少传一个。
        当两者都为 None 且 start_date 也为 None 时（例如定时任务以空参数触发），
        自动从 sync_history 计算建议起始日期，确保切片策略能被正确触发。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 8000) if cfg else 8000
        effective_strategy = sync_strategy or ((cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range')
        provider = self._get_provider(max_requests_per_minute)

        effective_start = start_date
        if not ts_code and not trade_date and not effective_start:
            effective_start = await self.get_suggested_start_date()
            logger.info(
                f"stk_nineturn 增量同步：未传 ts_code/trade_date/start_date，"
                f"自动使用建议起始日期 {effective_start}"
            )

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_nineturn,
            upsert_fn=self.stk_nineturn_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=effective_strategy,
            start_date=effective_start,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date,
                'freq': freq,
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
    ) -> Dict:
        """全量同步历史数据（按月切片，Redis Set 续继）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 8000) if cfg else 8000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_nineturn,
            upsert_fn=self.stk_nineturn_repo.bulk_upsert,
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
            fetch_kwargs={'freq': 'daily'},
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
            initial_count = len(df)
            df = df.drop_duplicates(subset=['ts_code', 'trade_date', 'freq'], keep='last')
            if len(df) < initial_count:
                logger.debug(f"删除了 {initial_count - len(df)} 条重复记录")

            required_fields = ['ts_code', 'trade_date']
            for field in required_fields:
                if field in df.columns:
                    df = df[df[field].notna()]

            if 'freq' not in df.columns or df['freq'].isna().any():
                df['freq'] = 'daily'

            logger.debug(f"数据验证完成，有效记录数: {len(df)}")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def resolve_default_date_range(self):
        """返回表中最新日期（作为 end_date），往前30天作为 start_date，用于前端回填。"""
        try:
            latest = await asyncio.to_thread(self.stk_nineturn_repo.get_latest_trade_date)
            if latest:
                end_dt = datetime.strptime(latest, '%Y-%m-%d')
                start_dt = end_dt - timedelta(days=30)
                return start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d')
            return None, None
        except Exception as e:
            logger.error(f"解析默认日期范围失败: {e}")
            return None, None

    async def get_stk_nineturn_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        freq: str = 'daily',
        limit: int = 100,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """获取神奇九转数据"""
        try:
            resolved_start = start_date
            resolved_end = end_date
            if not start_date and not end_date and not ts_code:
                resolved_start, resolved_end = await self.resolve_default_date_range()

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_by_date_range,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq,
                    limit=limit,
                    offset=offset,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_record_count,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq
                ),
                asyncio.to_thread(
                    self.stk_nineturn_repo.get_statistics,
                    start_date=resolved_start,
                    end_date=resolved_end,
                    ts_code=ts_code,
                    freq=freq
                )
            )

            if items:
                ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
                quotes = await asyncio.to_thread(stock_quote_cache._repo.get_quotes, ts_codes)
                for item in items:
                    item['name'] = quotes.get(item['ts_code'], {}).get('name', '')

            return {
                "items": items,
                "statistics": statistics,
                "total": total,
                "start_date": resolved_start,
                "end_date": resolved_end
            }

        except Exception as e:
            logger.error(f"获取神奇九转数据失败: {e}")
            raise

    async def get_turn_signals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        signal_type: str = 'all',
        limit: int = 50
    ) -> List[Dict]:
        """获取九转信号"""
        try:
            return await asyncio.to_thread(
                self.stk_nineturn_repo.get_turn_signals,
                start_date=start_date,
                end_date=end_date,
                signal_type=signal_type,
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取九转信号失败: {e}")
            raise

    async def get_latest_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """获取最新交易日期"""
        try:
            return await asyncio.to_thread(
                self.stk_nineturn_repo.get_latest_trade_date, ts_code=ts_code
            )
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
