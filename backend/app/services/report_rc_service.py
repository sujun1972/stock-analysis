"""
卖方盈利预测服务

处理卖方盈利预测数据的业务逻辑。
继承 TushareSyncBase，增量同步逻辑委托给基类。
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from app.repositories.report_rc_repository import ReportRcRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class ReportRcService(TushareSyncBase):
    """卖方盈利预测服务"""

    TABLE_KEY = 'report_rc'
    FULL_HISTORY_START_DATE = '20100101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:report_rc:full_history:progress'

    def __init__(self):
        super().__init__()
        self.report_rc_repo = ReportRcRepository()
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
        return await self.sync_report_rc(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_report_rc(
        self,
        ts_code: Optional[str] = None,
        report_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步卖方盈利预测数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时（by_month/by_week/by_date），
        按切片逐段请求并支持每段翻页（api_limit）。
        否则执行单次全量请求。

        Args:
            ts_code:       股票代码（单次请求分支使用）
            report_date:   研报日期 YYYYMMDD（单次请求分支使用）
            start_date:    时间范围起始 YYYYMMDD
            end_date:      时间范围结束 YYYYMMDD
            sync_strategy: 同步策略（来自 sync_configs.incremental_sync_strategy）
            max_requests_per_minute: 每分钟最大请求数
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 2000) if cfg else 2000
        provider = self._get_provider(max_requests_per_minute)

        result = await self.run_incremental_sync(
            fetch_fn=provider.get_report_rc,
            upsert_fn=self.report_rc_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='report_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'ts_code': ts_code,
                'report_date': report_date,
            },
        )

        # 触发全市场 value_metrics 重算：券商一致预期变化影响 IV 的 g_rate（研报路径）。
        # 新研报分布广泛，单只 mark_dirty 意义不大，直接触发全量 + 10 分钟冷却合并。
        try:
            from app.services.value_metrics import ValueMetricsTrigger
            total_records = (result or {}).get('total_records') or (result or {}).get('records') or 0
            if total_records > 0:
                ValueMetricsTrigger.trigger_full(source='report_rc')
        except Exception as e:
            logger.debug(f"[report_rc] 触发 value_metrics 全量重算失败（不影响主流程）: {e}")

        return result

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    async def get_report_rc_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        org_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict:
        """查询卖方盈利预测数据"""
        try:
            trade_date_fmt = trade_date.replace('-', '') if trade_date else None
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            items, total, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.report_rc_repo.get_by_date_range,
                    trade_date=trade_date_fmt,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_name=org_name,
                    page=page,
                    page_size=page_size,
                    sort_by=sort_by,
                    sort_order=sort_order,
                ),
                asyncio.to_thread(
                    self.report_rc_repo.get_total_count,
                    trade_date=trade_date_fmt,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    org_name=org_name,
                ),
                asyncio.to_thread(
                    self.report_rc_repo.get_statistics,
                    start_date=trade_date_fmt or start_date_fmt,
                    end_date=trade_date_fmt or end_date_fmt,
                    ts_code=ts_code,
                ),
            )

            return {'items': items, 'statistics': statistics, 'total': total}

        except Exception as e:
            logger.error(f"获取卖方盈利预测数据失败: {e}")
            raise

    async def get_latest_data(self) -> Dict:
        """获取最新数据信息"""
        try:
            latest_date = await asyncio.to_thread(self.report_rc_repo.get_latest_report_date)
            if not latest_date:
                return {'latest_date': None, 'data': []}
            items = await asyncio.to_thread(
                self.report_rc_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                page_size=100,
            )
            return {'latest_date': latest_date, 'data': items}
        except Exception as e:
            logger.error(f"获取最新卖方盈利预测数据失败: {e}")
            raise

    async def get_top_rated_stocks(
        self,
        report_date: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """获取高评级股票"""
        try:
            if not report_date:
                latest_date = await asyncio.to_thread(self.report_rc_repo.get_latest_report_date)
                if not latest_date:
                    return []
                report_date_fmt = latest_date
            else:
                report_date_fmt = report_date.replace('-', '')

            return await asyncio.to_thread(
                self.report_rc_repo.get_top_rated_stocks,
                report_date=report_date_fmt,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"获取高评级股票失败: {e}")
            raise

    async def resolve_default_report_date(self) -> Optional[str]:
        """返回最近有数据的研报日期（YYYY-MM-DD 格式），用于前端回填。"""
        latest = await asyncio.to_thread(self.report_rc_repo.get_latest_report_date)
        if latest and len(latest) == 8:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    async def get_suggested_start_date(self) -> Optional[str]:
        """
        计算增量同步的建议起始日期（YYYYMMDD）。

        逻辑：
          候选起始 = 今天 - incremental_default_days（从 sync_configs 读取，默认 30 天）
          上次结束 = sync_history 中最近一次增量成功的 data_end_date
          实际起始 = min(候选起始, 上次结束)，取两者中更早的，保证数据连续不遗漏
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 30) if cfg else 30

        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')

        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )

        if last_end and last_end < candidate:
            suggested = last_end
            logger.debug(
                f"[report_rc] 建议起始={suggested}（上次结束={last_end} < 候选={candidate}）"
            )
        else:
            suggested = candidate
            logger.debug(
                f"[report_rc] 建议起始={suggested}（候选={candidate}，上次结束={last_end}）"
            )

        return suggested

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
        """全量同步历史数据（Redis Set 续继，切片策略由 strategy 参数控制）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute or None)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_report_rc,
            upsert_fn=self.report_rc_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            progress_key=self.FULL_HISTORY_PROGRESS_KEY,
            strategy=strategy,
            start_date=start_date,
            full_history_start=self.FULL_HISTORY_START_DATE,
            concurrency=concurrency,
            api_limit=api_limit,
            max_requests_per_minute=max_requests_per_minute or None,
            update_state_fn=update_state_fn,
            table_key=self.TABLE_KEY,
        )

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _validate_and_clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证和清洗数据"""
        if df is None or df.empty:
            return df

        df = df.copy()

        required_fields = ['ts_code', 'report_date', 'org_name', 'quarter']
        for field in required_fields:
            if field not in df.columns:
                raise ValueError(f"缺少必需字段: {field}")

        df = df.dropna(subset=required_fields)

        if 'report_date' in df.columns:
            df['report_date'] = df['report_date'].astype(str)

        numeric_fields = [
            'op_rt', 'op_pr', 'tp', 'np',
            'eps', 'pe', 'rd', 'roe', 'ev_ebitda',
            'max_price', 'min_price',
        ]
        for field in numeric_fields:
            if field in df.columns:
                df[field] = df[field].apply(
                    lambda x: None if str(x).strip() in ('', 'nan', 'None') else x
                )

        logger.info(f"数据验证完成，剩余 {len(df)} 条有效数据")
        return df
