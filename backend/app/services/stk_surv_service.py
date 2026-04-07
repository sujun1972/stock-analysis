"""
机构调研表服务

负责机构调研数据的同步和查询业务逻辑。
继承 TushareSyncBase，同步逻辑委托给基类。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.stk_surv_repository import StkSurvRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class StkSurvService(TushareSyncBase):
    """机构调研表服务"""

    TABLE_KEY = 'stk_surv'
    FULL_HISTORY_START_DATE = '20100101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_surv:full_history:progress'

    def __init__(self):
        super().__init__()
        self.stk_surv_repo = StkSurvRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ StkSurvService initialized")

    # ------------------------------------------------------------------
    # 增量同步
    # ------------------------------------------------------------------

    async def sync_stk_surv(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步机构调研数据。

        机构调研接口使用 surv_date 作为日期字段（而非 trade_date）。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 100) if cfg else 100
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_surv,
            upsert_fn=self.stk_surv_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='surv_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
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
        api_limit = (cfg.get('api_limit') or 100) if cfg else 100
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_surv,
            upsert_fn=self.stk_surv_repo.bulk_upsert,
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
        required_columns = ['ts_code', 'surv_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        if 'surv_date' in df.columns:
            df['surv_date'] = df['surv_date'].astype(str).str.replace('-', '')
            invalid_dates = df[df['surv_date'].str.len() != 8]
            if not invalid_dates.empty:
                logger.warning(f"发现 {len(invalid_dates)} 条无效surv_date记录，将被过滤")
                df = df[df['surv_date'].str.len() == 8]

        df = df.drop_duplicates(subset=['ts_code', 'surv_date', 'fund_visitors'], keep='last')

        df = df.fillna({
            'name': '',
            'fund_visitors': '',
            'rece_place': '',
            'rece_mode': '',
            'rece_org': '',
            'org_type': '',
            'comp_rece': '',
            'content': ''
        })

        logger.debug(f"数据验证完成，有效数据: {len(df)} 条")
        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """格式化日期用于前端显示（YYYYMMDD -> YYYY-MM-DD）"""
        if not date_str or len(date_str) != 8:
            return date_str
        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_stk_surv_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        org_type: Optional[str] = None,
        rece_mode: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """获取机构调研数据"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_surv_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_type=org_type,
                    rece_mode=rece_mode,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_surv_repo.get_statistics,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt
                )
            )

            for item in items:
                if item['surv_date']:
                    item['surv_date'] = self._format_date_for_display(item['surv_date'])

            return {
                "items": items,
                "statistics": statistics,
                "total": statistics.get('total_records', len(items))
            }

        except Exception as e:
            logger.error(f"获取机构调研数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """获取统计信息"""
        try:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            return await asyncio.to_thread(
                self.stk_surv_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 20) -> Dict:
        """获取最新的机构调研数据"""
        try:
            latest_date = await asyncio.to_thread(self.stk_surv_repo.get_latest_date)
            if not latest_date:
                return {"items": [], "total": 0}

            items = await asyncio.to_thread(
                self.stk_surv_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=limit
            )

            for item in items:
                if item['surv_date']:
                    item['surv_date'] = self._format_date_for_display(item['surv_date'])

            return {"items": items, "total": len(items)}

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise
