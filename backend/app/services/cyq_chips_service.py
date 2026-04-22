"""
每日筹码分布数据同步服务

处理筹码分布数据的获取和存储。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories.cyq_chips_repository import CyqChipsRepository
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class CyqChipsService(TushareSyncBase):
    """每日筹码分布数据同步服务"""

    TABLE_KEY = 'cyq_chips'
    FULL_HISTORY_START_DATE = '20180101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:cyq_chips:full_history:progress'
    INCREMENTAL_PROGRESS_KEY = 'sync:cyq_chips:incremental:progress'

    def __init__(self):
        super().__init__()
        self.cyq_chips_repo = CyqChipsRepository()
        self.calendar_repo = TradingCalendarRepository()
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
    ) -> Dict[str, Any]:
        """标准增量同步入口（无参数时自动从 sync_configs 读取配置）。

        by_ts_code 策略走流式路径（见 _sync_incremental_by_ts_code），其他策略走
        sync_cyq_chips（单次请求数据量小，无需流式）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_ts_code') if cfg else 'by_ts_code'
        if start_date is None:
            start_date = await self.get_suggested_start_date()

        if sync_strategy == 'by_ts_code':
            return await self._sync_incremental_by_ts_code(
                start_date=start_date,
                end_date=end_date,
                max_requests_per_minute=max_requests_per_minute,
            )

        return await self.sync_cyq_chips(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def _sync_incremental_by_ts_code(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """by_ts_code 增量：流式处理（逐只 fetch → clean → upsert → 释放）。

        run_incremental_sync 会把所有 ts_code 的 DataFrame 聚合到内存再一次性 upsert。
        cyq_chips 每只股票每交易日 ~100 行价位数据，5000+ 只股票 × 回看窗口会吃几 GB
        内存被 OOM Killer SIGKILL。此方法复用 _full_sync_by_ts_code（每只独立 upsert
        后释放），内存常驻量从 O(全市场) 降到 O(单只)。

        幂等：进入时清空 Set，全程 sadd 已完成的 ts_code，同一次任务内重试可续继；
        跨次调度每次都从零覆盖近 N 天窗口。
        """
        from app.core.redis_lock import redis_client

        if redis_client is None:
            # 降级到 run_incremental_sync 就是原 OOM 路径，拒绝执行比埋雷更安全
            raise RuntimeError(
                f"[{self.TABLE_KEY}] 增量 by_ts_code 依赖 Redis 做幂等，Redis 不可用"
            )

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        concurrency = (cfg.get('full_sync_concurrency') or 5) if cfg else 5
        provider = self._get_provider(max_requests_per_minute)

        await asyncio.to_thread(redis_client.delete, self.INCREMENTAL_PROGRESS_KEY)

        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            self.TABLE_KEY, 'incremental', 'by_ts_code', start_date,
        )

        # 流式路径每只独立 upsert，拿不到整体 max(trade_date)，用 end_date 作为近似；
        # records=0 时返回 None，与 run_incremental_sync 对齐
        effective_end = end_date or datetime.now().strftime('%Y%m%d')

        try:
            logger.info(
                f"[{self.TABLE_KEY}] 增量 by_ts_code（流式）: "
                f"start={start_date} end={effective_end} api_limit={api_limit} concurrency={concurrency}"
            )

            result = await self._full_sync_by_ts_code(
                redis_client=redis_client,
                fetch_fn=provider.get_cyq_chips,
                upsert_fn=self.cyq_chips_repo.bulk_upsert,
                clean_fn=self._validate_and_clean_data,
                progress_key=self.INCREMENTAL_PROGRESS_KEY,
                start_date=start_date,
                full_history_start=start_date,
                concurrency=concurrency,
                api_limit=api_limit,
                max_requests_per_minute=max_requests_per_minute or 0,
                update_state_fn=None,
                fetch_kwargs={},
                table_key=self.TABLE_KEY,
            )

            records = result.get('records', 0)
            status = result.get('status', 'success')
            actual_end_date = effective_end if records > 0 else None

            if status == 'success':
                await asyncio.to_thread(
                    self.sync_history_repo.complete,
                    history_id, 'success', records, actual_end_date, None,
                )
                return {
                    "status": "success",
                    "records": records,
                    "data_end_date": actual_end_date,
                    "message": result.get('message', f"成功同步 {records} 条数据"),
                }

            err = result.get('message') or 'unknown'
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', records, actual_end_date, err,
            )
            return {"status": "error", "records": records, "error": err}

        except Exception as e:
            logger.error(f"[{self.TABLE_KEY}] 增量 by_ts_code 失败: {e}")
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            raise

    async def sync_cyq_chips(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict[str, Any]:
        """增量同步筹码分布数据。

        cyq_chips 接口要求 ts_code 必填，
        支持 by_ts_code（逐只股票）和 by_date（按 trade_date 逐日切片）策略。
        """
        if sync_strategy and sync_strategy not in ('by_ts_code', 'by_date', 'none'):
            logger.warning(
                f"[cyq_chips] 不支持 sync_strategy={sync_strategy}，强制使用 by_ts_code"
            )
            sync_strategy = 'by_ts_code'

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_cyq_chips,
            upsert_fn=self.cyq_chips_repo.bulk_upsert,
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
    ) -> Dict[str, Any]:
        """全量同步历史数据（逐只股票请求，Redis Set 续继）

        cyq_chips 接口服务端要求 ts_code 或 trade_date 至少传一个，
        不支持纯按日期范围全市场查询，只能使用 by_ts_code 策略。
        """
        if strategy != 'by_ts_code':
            logger.warning(
                f"[cyq_chips] 接口不支持按日期范围全市场查询，"
                f"忽略 strategy={strategy}，强制使用 by_ts_code"
            )
            strategy = 'by_ts_code'

        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_cyq_chips,
            upsert_fn=self.cyq_chips_repo.bulk_upsert,
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

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗数据"""
        required_cols = ['ts_code', 'trade_date', 'price', 'percent']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        df = df.dropna(subset=['ts_code', 'trade_date', 'price'])
        df['ts_code'] = df['ts_code'].astype(str)
        df['trade_date'] = df['trade_date'].astype(str)
        df = df.drop_duplicates(subset=['ts_code', 'trade_date', 'price'], keep='last')

        logger.debug(f"数据验证完成，有效记录数: {len(df)}")
        return df

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def _is_data_stale(self, ts_code: str) -> bool:
        """判断指定股票的筹码数据是否过时。"""
        latest_in_db = self.cyq_chips_repo.get_latest_trade_date(ts_code)
        if not latest_in_db:
            return True
        latest_trading_day = self.calendar_repo.get_latest_trading_day()
        if not latest_trading_day:
            return False
        if hasattr(latest_trading_day, 'strftime'):
            latest_trading_day = latest_trading_day.strftime('%Y%m%d')
        return latest_in_db < latest_trading_day

    async def get_cyq_chips_with_auto_sync(self, ts_code: str) -> list:
        """获取指定股票的最新筹码分布数据，若数据过时则先同步再返回。"""
        stale = await asyncio.to_thread(self._is_data_stale, ts_code)
        if stale:
            logger.info(f"筹码数据不存在或过时，自动同步: {ts_code}")
            await self.sync_cyq_chips(ts_code=ts_code)

        latest_date = await asyncio.to_thread(
            self.cyq_chips_repo.get_latest_trade_date, ts_code
        )
        if not latest_date:
            return []

        items = await asyncio.to_thread(
            self.cyq_chips_repo.get_by_code_and_date_range,
            ts_code=ts_code,
            start_date=latest_date,
            end_date=latest_date,
            limit=2000
        )
        return items

    async def resolve_default_trade_date(self) -> Optional[str]:
        """返回最近有数据的交易日期（YYYY-MM-DD），用于前端日期选择器回填。"""
        latest = await asyncio.to_thread(self.cyq_chips_repo.get_latest_trade_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_cyq_chips_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """查询筹码分布数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.cyq_chips_repo.get_by_date_range,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.cyq_chips_repo.get_total_count,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                ),
                asyncio.to_thread(
                    self.cyq_chips_repo.get_statistics,
                    ts_code=ts_code,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                )
            )

            return {"items": items, "statistics": statistics, "total": total}

        except Exception as e:
            logger.error(f"查询筹码分布数据失败: {e}")
            raise

    async def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取筹码分布统计信息"""
        try:
            return await asyncio.to_thread(
                self.cyq_chips_repo.get_statistics,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"获取筹码分布统计信息失败: {e}")
            raise

    async def get_latest_data(self, ts_code: Optional[str] = None) -> Dict[str, Any]:
        """获取最新筹码分布数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.cyq_chips_repo.get_latest_trade_date,
                ts_code=ts_code
            )
            if not latest_date:
                return {"latest_date": None, "items": []}

            if ts_code:
                items = await asyncio.to_thread(
                    self.cyq_chips_repo.get_by_code_and_date_range,
                    ts_code=ts_code,
                    start_date=latest_date,
                    end_date=latest_date,
                    limit=1000
                )
            else:
                items = await asyncio.to_thread(
                    self.cyq_chips_repo.get_by_trade_date,
                    trade_date=latest_date,
                    ts_code=None,
                    limit=1000
                )

            return {"latest_date": latest_date, "items": items}

        except Exception as e:
            logger.error(f"获取最新筹码分布数据失败: {e}")
            raise
