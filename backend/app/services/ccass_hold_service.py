"""
中央结算系统持股汇总数据服务

处理中央结算系统持股汇总数据的业务逻辑。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.ccass_hold_repository import CcassHoldRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class CcassHoldService(TushareSyncBase):
    """中央结算系统持股汇总数据服务"""

    TABLE_KEY = 'ccass_hold'
    FULL_HISTORY_START_DATE = '20160401'
    FULL_HISTORY_PROGRESS_KEY = 'sync:ccass_hold:full_history:progress'

    def __init__(self):
        super().__init__()
        self.ccass_hold_repo = CcassHoldRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ CcassHoldService initialized")

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_ccass_hold(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步中央结算系统持股汇总数据。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_ccass_hold,
            upsert_fn=self.ccass_hold_repo.bulk_upsert,
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
                'hk_code': hk_code,
                'trade_date': trade_date,
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
        api_limit = (cfg.get('api_limit') or 3000) if cfg else 3000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_ccass_hold,
            upsert_fn=self.ccass_hold_repo.bulk_upsert,
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

            numeric_fields = ['shareholding', 'hold_nums', 'hold_ratio']
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
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.ccass_hold_repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.ccass_hold_repo.get_latest_trade_date)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_ccass_hold_data(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict:
        """查询中央结算系统持股汇总数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            if trade_date_fmt and not start_date_fmt and not end_date_fmt:
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.ccass_hold_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    hk_code=hk_code,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order
                ),
                asyncio.to_thread(
                    self.ccass_hold_repo.get_total_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    hk_code=hk_code
                ),
                asyncio.to_thread(
                    self.ccass_hold_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {"items": items, "statistics": statistics, "total": total}

        except Exception as e:
            logger.error(f"获取中央结算系统持股汇总数据失败: {e}")
            raise

    async def get_latest_data(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        limit: int = 10
    ) -> Dict:
        """获取最新的中央结算系统持股汇总数据"""
        try:
            latest_date = await asyncio.to_thread(
                self.ccass_hold_repo.get_latest_trade_date, ts_code=ts_code
            )
            if not latest_date:
                return {"latest_date": None, "items": [], "total": 0}

            items = await asyncio.to_thread(
                self.ccass_hold_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                ts_code=ts_code,
                hk_code=hk_code,
                limit=limit
            )

            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            formatted_date = None
            if latest_date and len(latest_date) == 8:
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

            return {"latest_date": formatted_date, "items": items, "total": len(items)}

        except Exception as e:
            logger.error(f"获取最新中央结算系统持股汇总数据失败: {e}")
            raise

    async def get_top_shareholding(self, trade_date: str, limit: int = 20) -> List[Dict]:
        """获取持股量排名前N的股票"""
        try:
            trade_date_fmt = trade_date.replace('-', '')
            items = await asyncio.to_thread(
                self.ccass_hold_repo.get_top_by_shareholding,
                trade_date=trade_date_fmt,
                limit=limit
            )
            for item in items:
                if item.get('trade_date'):
                    date_str = item['trade_date']
                    if len(date_str) == 8:
                        item['trade_date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            return items
        except Exception as e:
            logger.error(f"获取持股量排名失败: {e}")
            raise
