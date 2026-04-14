"""
交易日历服务

用于获取最近交易日等日期相关功能，以及从 Tushare 同步 trade_cal 数据。

重构说明（2026-03-20）:
- 使用 TradingCalendarRepository 替代直接 SQL
- 移除 SQLAlchemy Session 依赖
- 统一异步和同步接口
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from app.repositories.trading_calendar_repository import TradingCalendarRepository
from app.repositories.sync_history_repository import SyncHistoryRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class TradingCalendarService:
    """交易日历服务"""

    def __init__(self):
        """初始化服务"""
        self.calendar_repo = TradingCalendarRepository()
        self.provider_factory = DataProviderFactory()
        self.sync_history_repo = SyncHistoryRepository()
        logger.debug("✓ TradingCalendarService initialized")

    # ==================== 数据查询方法 ====================

    async def get_calendar_data(
        self,
        exchange: str = 'SSE',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[str] = None,
        page: int = 1,
        page_size: int = 30
    ) -> Dict:
        """
        获取交易日历数据（分页）

        Args:
            exchange: 交易所代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            is_open: 是否交易 '0'休市 '1'交易
            page: 页码（从1开始）
            page_size: 每页记录数

        Returns:
            数据字典，包含 items、total、page、page_size
        """
        # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
        start_date_fmt = start_date.replace('-', '') if start_date else '19900101'
        end_date_fmt = end_date.replace('-', '') if end_date else '29991231'

        offset = (page - 1) * page_size

        items, total = await asyncio.gather(
            asyncio.to_thread(
                self.calendar_repo.get_calendar_paged,
                exchange=exchange,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                is_open=is_open,
                limit=page_size,
                offset=offset
            ),
            asyncio.to_thread(
                self.calendar_repo.get_calendar_count,
                exchange=exchange,
                start_date=start_date_fmt,
                end_date=end_date_fmt,
                is_open=is_open
            )
        )

        # 日期格式转换（YYYYMMDD -> YYYY-MM-DD）
        for item in items:
            if item.get('cal_date'):
                item['cal_date'] = self._format_date(item['cal_date'])
            if item.get('pretrade_date'):
                item['pretrade_date'] = self._format_date(item['pretrade_date'])

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    async def get_statistics(
        self,
        year: Optional[int] = None,
        exchange: str = 'SSE'
    ) -> Dict:
        """
        获取交易日历统计信息

        Args:
            year: 年份（默认为当前年份）
            exchange: 交易所代码

        Returns:
            统计信息字典
        """
        return await asyncio.to_thread(
            self.calendar_repo.get_statistics,
            year=year,
            exchange=exchange
        )

    async def get_latest_info(self, exchange: str = 'SSE') -> Dict:
        """
        获取最新交易日信息

        Args:
            exchange: 交易所代码

        Returns:
            最新交易日信息
        """
        latest_date = await asyncio.to_thread(
            self.calendar_repo.get_latest_trading_day,
            exchange=exchange
        )
        return {
            "latest_trading_day": self._format_date(latest_date) if latest_date else None,
            "exchange": exchange
        }

    # ==================== 数据同步方法 ====================

    async def sync_trade_calendar(
        self,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        从 Tushare 同步交易日历数据

        Args:
            exchange: 交易所代码（可选，默认同步 SSE 和 SZSE）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            同步结果字典
        """
        # 默认同步主要交易所
        exchanges_to_sync = [exchange] if exchange else ['SSE', 'SZSE']

        total_records = 0

        # 记录 sync_history
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create,
            'trade_cal', 'incremental', None, start_date,
        )

        try:
            provider = self._get_provider()

            for exch in exchanges_to_sync:
                logger.info(f"开始同步交易日历: exchange={exch}, start_date={start_date}, end_date={end_date}")

                # 从 Tushare 获取数据
                df = await asyncio.to_thread(
                    provider.get_trade_calendar,
                    exchange=exch,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is None or df.empty:
                    logger.warning(f"未获取到交易日历数据: exchange={exch}")
                    continue

                # 数据验证和清洗
                df = self._validate_and_clean_data(df, exch)

                # 批量插入数据库
                records = await asyncio.to_thread(
                    self.calendar_repo.bulk_upsert_calendar,
                    df,
                    exch
                )

                total_records += records
                logger.info(f"✓ 交易日历同步完成 [{exch}]: {records} 条记录")

            logger.info(f"✓ 交易日历全部同步完成: {total_records} 条记录")
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'success', total_records, end_date, None,
            )
            return {
                "status": "success",
                "message": f"成功同步 {total_records} 条交易日历记录",
                "records": total_records,
                "exchanges": exchanges_to_sync
            }

        except Exception as e:
            logger.error(f"同步交易日历数据失败: {e}")
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', 0, None, str(e),
            )
            return {
                "status": "error",
                "message": f"同步失败: {str(e)}",
                "records": 0
            }

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    def _validate_and_clean_data(self, df: pd.DataFrame, exchange: str) -> pd.DataFrame:
        """数据验证和清洗"""
        # 确保必需列存在
        required_columns = ['cal_date', 'is_open']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 如果没有 exchange 列，添加
        if 'exchange' not in df.columns:
            df['exchange'] = exchange

        # 数值类型转换
        df['is_open'] = pd.to_numeric(df['is_open'], errors='coerce').fillna(0).astype(int)

        # 删除 cal_date 为空的记录
        df = df.dropna(subset=['cal_date'])

        logger.info(f"数据清洗完成，保留 {len(df)} 条有效记录")
        return df

    def _format_date(self, date_str) -> str:
        """格式化日期字符串（YYYYMMDD -> YYYY-MM-DD）"""
        if not date_str:
            return date_str
        date_str = str(date_str)
        if len(date_str) != 8:
            return date_str
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # ==================== 原有方法（兼容保留）====================


    async def get_latest_trading_day(
        self,
        reference_date: Optional[datetime] = None,
        exchange: str = 'SSE'
    ) -> str:
        """
        获取最近的交易日（异步版本）

        Args:
            reference_date: 参考日期，默认为当前日期
            exchange: 交易所代码

        Returns:
            最近交易日，格式为YYYYMMDD
        """
        if reference_date is None:
            reference_date = datetime.now()

        ref_date_str = reference_date.strftime("%Y%m%d")

        try:
            # 1. 先尝试从交易日历表获取
            latest_day = await asyncio.to_thread(
                self.calendar_repo.get_latest_trading_day,
                ref_date_str,
                exchange
            )

            if latest_day:
                logger.info(f"从交易日历获取到最近交易日: {latest_day}")
                return latest_day

            # 2. 如果交易日历表为空，尝试从数据表获取
            latest_data_date = await asyncio.to_thread(
                self.calendar_repo.get_latest_data_date_from_tables
            )

            if latest_data_date and latest_data_date <= ref_date_str:
                logger.info(f"从数据表获取到最近交易日: {latest_data_date}")
                return latest_data_date

            # 3. 如果都没有数据，使用回退策略
            fallback_date = await asyncio.to_thread(
                self.calendar_repo.calculate_fallback_trading_day,
                reference_date
            )

            logger.warning(f"未找到交易日历和数据，使用回退日期: {fallback_date}")
            return fallback_date

        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            # 出错时使用安全的回退值
            fallback_date = self.calendar_repo.calculate_fallback_trading_day(reference_date)
            return fallback_date

    def get_latest_trading_day_sync(
        self,
        reference_date: Optional[datetime] = None,
        exchange: str = 'SSE'
    ) -> str:
        """
        获取最近的交易日（同步版本，用于 Celery 任务）

        Args:
            reference_date: 参考日期，默认为当前日期
            exchange: 交易所代码

        Returns:
            最近交易日，格式为YYYYMMDD
        """
        if reference_date is None:
            reference_date = datetime.now()

        ref_date_str = reference_date.strftime("%Y%m%d")

        try:
            # 1. 先尝试从交易日历表获取
            latest_day = self.calendar_repo.get_latest_trading_day(
                ref_date_str,
                exchange
            )

            if latest_day:
                logger.info(f"从交易日历获取到最近交易日: {latest_day}")
                return latest_day

            # 2. 如果交易日历表为空，尝试从数据表获取
            latest_data_date = self.calendar_repo.get_latest_data_date_from_tables()

            if latest_data_date and latest_data_date <= ref_date_str:
                logger.info(f"从数据表获取到最近交易日: {latest_data_date}")
                return latest_data_date

            # 3. 如果都没有数据，使用回退策略
            fallback_date = self.calendar_repo.calculate_fallback_trading_day(reference_date)

            logger.warning(f"未找到交易日历和数据，使用回退日期: {fallback_date}")
            return fallback_date

        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            # 出错时使用安全的回退值
            fallback_date = self.calendar_repo.calculate_fallback_trading_day(reference_date)
            return fallback_date

    async def get_latest_data_date(self) -> str:
        """获取数据库中最新的数据日期（异步版本）"""
        try:
            latest_date = await asyncio.to_thread(
                self.calendar_repo.get_latest_data_date_from_tables
            )
            if latest_date:
                logger.info(f"数据库中最新数据日期: {latest_date}")
                return latest_date
            return await asyncio.to_thread(
                self.calendar_repo.calculate_fallback_trading_day
            )
        except Exception as e:
            logger.error(f"获取最新数据日期失败: {e}")
            return self.calendar_repo.calculate_fallback_trading_day()

    def get_latest_data_date_sync(self) -> str:
        """获取数据库中最新的数据日期（同步版本）"""
        try:
            latest_date = self.calendar_repo.get_latest_data_date_from_tables()
            if latest_date:
                logger.info(f"数据库中最新数据日期: {latest_date}")
                return latest_date
            return self.calendar_repo.calculate_fallback_trading_day()
        except Exception as e:
            logger.error(f"获取最新数据日期失败: {e}")
            return self.calendar_repo.calculate_fallback_trading_day()


# 创建全局实例（向后兼容）
trading_calendar_service = TradingCalendarService()
