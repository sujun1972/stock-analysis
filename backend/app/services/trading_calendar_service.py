"""
交易日历服务
用于获取最近交易日等日期相关功能
"""

from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_async_db, get_db
from app.core.config import settings


class TradingCalendarService:
    """交易日历服务"""

    def __init__(self):
        # 创建同步数据库引擎（用于在Celery任务中使用）
        self.engine = create_engine(settings.DATABASE_URL)
        self.SessionLocal = sessionmaker(bind=self.engine)

    async def get_latest_trading_day(self, reference_date: Optional[datetime] = None) -> str:
        """
        获取最近的交易日

        Args:
            reference_date: 参考日期，默认为当前日期

        Returns:
            最近交易日，格式为YYYYMMDD
        """
        if reference_date is None:
            reference_date = datetime.now()

        try:
            async with get_async_db() as db:
                # 先尝试从交易日历表获取
                query = text("""
                    SELECT cal_date
                    FROM trade_cal
                    WHERE is_open = 1
                    AND cal_date <= :ref_date
                    ORDER BY cal_date DESC
                    LIMIT 1
                """)

                ref_date_str = reference_date.strftime("%Y%m%d")
                result = await db.execute(query, {"ref_date": ref_date_str})
                row = result.fetchone()

                if row:
                    logger.info(f"从交易日历获取到最近交易日: {row[0]}")
                    return row[0]

                # 如果交易日历表不存在或为空，尝试从日线数据表获取
                query = text("""
                    SELECT DISTINCT trade_date
                    FROM stock_daily
                    WHERE trade_date <= :ref_date
                    ORDER BY trade_date DESC
                    LIMIT 1
                """)

                result = await db.execute(query, {"ref_date": ref_date_str})
                row = result.fetchone()

                if row:
                    logger.info(f"从日线数据获取到最近交易日: {row[0]}")
                    return row[0]

                # 如果都没有数据，使用回退策略
                # 通常A股最新数据会有1-2天延迟，周末和节假日不交易
                fallback_date = reference_date - timedelta(days=3)

                # 如果是周一，往前推到上周五
                if reference_date.weekday() == 0:  # Monday
                    fallback_date = reference_date - timedelta(days=3)
                # 如果是周日，往前推到周五
                elif reference_date.weekday() == 6:  # Sunday
                    fallback_date = reference_date - timedelta(days=2)
                # 如果是周六，往前推到周五
                elif reference_date.weekday() == 5:  # Saturday
                    fallback_date = reference_date - timedelta(days=1)
                else:
                    # 工作日，往前推1天
                    fallback_date = reference_date - timedelta(days=1)

                fallback_str = fallback_date.strftime("%Y%m%d")
                logger.warning(f"未找到交易日历和日线数据，使用回退日期: {fallback_str}")
                return fallback_str

        except Exception as e:
            logger.error(f"获取最近交易日失败: {e}")
            # 出错时使用安全的回退值
            fallback_date = reference_date - timedelta(days=3)
            return fallback_date.strftime("%Y%m%d")

    async def get_latest_data_date(self) -> str:
        """
        获取数据库中最新的数据日期

        Returns:
            最新数据日期，格式为YYYYMMDD
        """
        try:
            async with get_async_db() as db:
                # 从多个表中查找最新日期
                queries = [
                    "SELECT MAX(trade_date) FROM stock_daily",
                    "SELECT MAX(trade_date) FROM daily_basic",
                    "SELECT MAX(trade_date) FROM moneyflow",
                    "SELECT MAX(trade_date) FROM hk_hold"
                ]

                latest_dates = []

                for query_str in queries:
                    try:
                        result = await db.execute(text(query_str))
                        row = result.fetchone()
                        if row and row[0]:
                            latest_dates.append(row[0])
                    except Exception as e:
                        # 某个表可能不存在，忽略错误
                        logger.debug(f"查询失败（表可能不存在）: {query_str}, 错误: {e}")
                        continue

                if latest_dates:
                    # 返回最新的日期
                    latest = max(latest_dates)
                    logger.info(f"数据库中最新数据日期: {latest}")
                    return latest
                else:
                    # 如果没有任何数据，基于当前日期计算最近的交易日
                    return self._calculate_latest_trading_day()

        except Exception as e:
            logger.error(f"获取最新数据日期失败: {e}")
            # 返回基于当前日期计算的交易日
            return self._calculate_latest_trading_day()

    def get_latest_data_date_sync(self) -> str:
        """
        获取数据库中最新的数据日期（同步版本，用于Celery任务）

        Returns:
            最新数据日期，格式为YYYYMMDD
        """
        try:
            with self.SessionLocal() as db:
                # 从多个表中查找最新日期
                queries = [
                    "SELECT MAX(trade_date) FROM stock_daily",
                    "SELECT MAX(trade_date) FROM daily_basic",
                    "SELECT MAX(trade_date) FROM moneyflow",
                    "SELECT MAX(trade_date) FROM hk_hold"
                ]

                latest_dates = []

                for query_str in queries:
                    try:
                        result = db.execute(text(query_str))
                        row = result.fetchone()
                        if row and row[0]:
                            latest_dates.append(row[0])
                    except Exception as e:
                        # 某个表可能不存在，忽略错误
                        logger.debug(f"查询失败（表可能不存在）: {query_str}, 错误: {e}")
                        continue

                if latest_dates:
                    # 返回最新的日期
                    latest = max(latest_dates)
                    logger.info(f"数据库中最新数据日期: {latest}")
                    return latest
                else:
                    # 如果没有任何数据，基于当前日期计算最近的交易日
                    return self._calculate_latest_trading_day()

        except Exception as e:
            logger.error(f"获取最新数据日期失败: {e}")
            # 返回基于当前日期计算的交易日
            return self._calculate_latest_trading_day()

    def _calculate_latest_trading_day(self) -> str:
        """
        基于当前日期计算最近的交易日

        Returns:
            交易日期，格式为YYYYMMDD
        """
        today = datetime.now()

        # 如果是周末，回退到上周五
        # 周一是0，周日是6
        if today.weekday() == 5:  # 周六
            today = today - timedelta(days=1)
        elif today.weekday() == 6:  # 周日
            today = today - timedelta(days=2)

        # 如果是工作日但时间早于15:30（市场收盘时间），使用前一个交易日
        if today.weekday() < 5:  # 周一到周五
            if today.hour < 15 or (today.hour == 15 and today.minute < 30):
                # 回退到前一个交易日
                today = today - timedelta(days=1)
                # 如果回退后是周末，继续回退到周五
                if today.weekday() == 5:  # 周六
                    today = today - timedelta(days=1)
                elif today.weekday() == 6:  # 周日
                    today = today - timedelta(days=2)

        # 格式化为YYYYMMDD
        result = today.strftime("%Y%m%d")
        logger.info(f"基于当前时间计算的最近交易日: {result}")
        return result


# 创建全局实例
trading_calendar_service = TradingCalendarService()