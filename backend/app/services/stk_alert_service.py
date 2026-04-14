"""
交易所重点提示证券服务

负责交易所重点提示证券数据的同步和查询业务逻辑
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from loguru import logger

from app.repositories.stk_alert_repository import StkAlertRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from app.services.tushare_sync_base import TushareSyncBase


class StkAlertService(TushareSyncBase):
    """交易所重点提示证券服务"""

    TABLE_KEY = 'stk_alert'
    FULL_HISTORY_START_DATE = '20050101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:stk_alert:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:stk_alert:full_history:lock'

    def __init__(self):
        super().__init__()
        self.stk_alert_repo = StkAlertRepository()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ StkAlertService initialized")

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        strategy: str = 'by_month',
        update_state_fn=None,
        max_requests_per_minute: int = 0,
    ) -> Dict:
        """全量同步交易所重点提示证券历史数据（按月切片，支持 Redis 续继）"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_stk_alert,
            upsert_fn=self.stk_alert_repo.bulk_upsert,
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
        return await self.sync_stk_alert(
            start_date=start_date,
            end_date=end_date,
            sync_strategy=sync_strategy,
            max_requests_per_minute=max_requests_per_minute,
        )

    async def sync_stk_alert(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        sync_strategy: Optional[str] = None,
        max_requests_per_minute: Optional[int] = None,
    ) -> Dict:
        """增量同步交易所重点提示证券数据。

        当 start_date 存在且 sync_strategy 为日期切片策略时，按切片逐段请求并支持翻页。
        """
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)

        return await self.run_incremental_sync(
            fetch_fn=provider.get_stk_alert,
            upsert_fn=self.stk_alert_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            table_key=self.TABLE_KEY,
            date_col='start_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
            extra_fetch_kwargs={
                'trade_date': trade_date,
                'ts_code': ts_code,
            },
        )

    async def get_stk_alert_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取交易所重点提示证券数据

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据字典，包含items和total
        """
        try:
            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
            end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

            # 获取数据
            items, total = await asyncio.gather(
                asyncio.to_thread(
                    self.stk_alert_repo.get_by_date_range,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code,
                    limit=limit,
                    offset=offset
                ),
                asyncio.to_thread(
                    self.stk_alert_repo.get_count,
                    start_date=start_date_fmt,
                    end_date=end_date_fmt,
                    ts_code=ts_code
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取交易所重点提示证券数据失败: {e}")
            raise

    async def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）

        Returns:
            统计信息字典
        """
        try:
            # 日期格式转换
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

            stats = await asyncio.to_thread(
                self.stk_alert_repo.get_statistics,
                start_date=start_date_fmt,
                end_date=end_date_fmt
            )

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    async def get_latest_data(self, limit: int = 20) -> Dict:
        """
        获取最新的重点提示证券数据

        Args:
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 获取最新提示起始日期
            latest_date = await asyncio.to_thread(
                self.stk_alert_repo.get_latest_start_date
            )

            if not latest_date:
                return {"items": [], "total": 0}

            # 获取该日期的数据
            items = await asyncio.to_thread(
                self.stk_alert_repo.get_by_date_range,
                start_date=latest_date,
                end_date=latest_date,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取最新数据失败: {e}")
            raise

    async def get_active_alerts(self, current_date: Optional[str] = None, limit: int = 100) -> Dict:
        """
        获取当前仍在有效期内的重点提示证券

        Args:
            current_date: 当前日期（YYYY-MM-DD格式），默认为今天
            limit: 返回记录数限制

        Returns:
            数据字典
        """
        try:
            # 如果未提供日期，使用今天
            if not current_date:
                current_date = datetime.now().strftime('%Y-%m-%d')

            # 日期格式转换：YYYY-MM-DD -> YYYYMMDD
            current_date_fmt = current_date.replace('-', '')

            # 获取当前有效的重点提示证券
            items = await asyncio.to_thread(
                self.stk_alert_repo.get_active_alerts,
                current_date=current_date_fmt,
                limit=limit
            )

            # 日期格式转换
            for item in items:
                if item['start_date']:
                    item['start_date'] = self._format_date_for_display(item['start_date'])
                if item['end_date']:
                    item['end_date'] = self._format_date_for_display(item['end_date'])

            return {
                "items": items,
                "total": len(items)
            }

        except Exception as e:
            logger.error(f"获取当前有效的重点提示证券失败: {e}")
            raise

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

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        # 确保必需列存在
        required_columns = ['ts_code', 'start_date']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 确保日期格式为 YYYYMMDD（8位）
        for date_col in ['start_date', 'end_date']:
            if date_col in df.columns:
                df[date_col] = df[date_col].astype(str).str.replace('-', '')
                # 验证日期格式
                invalid_dates = df[df[date_col].str.len() != 8]
                if not invalid_dates.empty:
                    logger.warning(f"发现 {len(invalid_dates)} 条无效{date_col}记录，将被过滤")
                    df = df[df[date_col].str.len() == 8]

        # 删除重复记录
        df = df.drop_duplicates(subset=['ts_code', 'start_date'], keep='last')

        # 处理空值
        df = df.fillna({
            'name': '',
            'end_date': '',
            'type': ''
        })

        return df

    def _format_date_for_display(self, date_str: str) -> str:
        """
        格式化日期用于前端显示

        Args:
            date_str: YYYYMMDD格式的日期字符串

        Returns:
            YYYY-MM-DD格式的日期字符串
        """
        if not date_str or len(date_str) != 8:
            return date_str

        try:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        except Exception:
            return date_str
