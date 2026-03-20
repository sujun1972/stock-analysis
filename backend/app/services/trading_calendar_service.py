"""
交易日历服务

用于获取最近交易日等日期相关功能。

重构说明（2026-03-20）:
- 使用 TradingCalendarRepository 替代直接 SQL
- 移除 SQLAlchemy Session 依赖
- 统一异步和同步接口
"""

import asyncio
from typing import Optional
from datetime import datetime
from loguru import logger

from app.repositories.trading_calendar_repository import TradingCalendarRepository


class TradingCalendarService:
    """交易日历服务"""

    def __init__(self):
        """初始化服务"""
        self.calendar_repo = TradingCalendarRepository()
        logger.debug("✓ TradingCalendarService initialized")

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
