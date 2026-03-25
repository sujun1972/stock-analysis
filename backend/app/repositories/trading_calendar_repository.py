"""
交易日历 Repository

负责 trade_cal 和 trading_calendar 表的数据访问操作。
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class TradingCalendarRepository(BaseRepository):
    """
    交易日历数据访问层

    职责:
    - 交易日历数据的查询和管理
    - 交易日判断
    - 最近交易日计算

    支持两个表:
    - trade_cal: Tushare 标准交易日历（简化版）
    - trading_calendar: 自定义交易日历（包含节假日信息）
    """

    # 默认使用 Tushare 标准表
    TABLE_NAME = "trade_cal"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ TradingCalendarRepository initialized")

    # ==================== 查询操作 ====================

    def get_latest_trading_day(
        self,
        reference_date: Optional[str] = None,
        exchange: str = 'SSE'
    ) -> Optional[str]:
        """
        获取最近的交易日

        Args:
            reference_date: 参考日期，格式：YYYYMMDD（默认为今天）
            exchange: 交易所代码 (SSE/SZSE)

        Returns:
            最近交易日，格式：YYYYMMDD

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> latest = repo.get_latest_trading_day()
            >>> print(latest)  # '20260318'
        """
        if reference_date is None:
            reference_date = datetime.now().strftime("%Y%m%d")

        query = """
            SELECT cal_date
            FROM trade_cal
            WHERE is_open = 1
              AND exchange = %s
              AND cal_date <= %s
            ORDER BY cal_date DESC
            LIMIT 1
        """

        try:
            result = self.execute_query(query, (exchange, reference_date))
            if result:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"查询最近交易日失败: {e}")
            raise QueryError(
                "查询最近交易日失败",
                error_code="LATEST_TRADING_DAY_QUERY_FAILED",
                reason=str(e)
            )

    def get_next_trading_day(
        self,
        reference_date: str,
        exchange: str = 'SSE'
    ) -> Optional[str]:
        """
        获取下一个交易日

        Args:
            reference_date: 参考日期，格式：YYYYMMDD
            exchange: 交易所代码

        Returns:
            下一个交易日，格式：YYYYMMDD

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> next_day = repo.get_next_trading_day('20260318')
            >>> print(next_day)  # '20260319'
        """
        query = """
            SELECT cal_date
            FROM trade_cal
            WHERE is_open = 1
              AND exchange = %s
              AND cal_date > %s
            ORDER BY cal_date ASC
            LIMIT 1
        """

        try:
            result = self.execute_query(query, (exchange, reference_date))
            if result:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"查询下一个交易日失败: {e}")
            raise QueryError(
                "查询下一个交易日失败",
                error_code="NEXT_TRADING_DAY_QUERY_FAILED",
                reason=str(e)
            )

    def is_trading_day(
        self,
        check_date: str,
        exchange: str = 'SSE'
    ) -> bool:
        """
        判断指定日期是否为交易日

        Args:
            check_date: 日期，格式：YYYYMMDD
            exchange: 交易所代码

        Returns:
            是否为交易日

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> is_trading = repo.is_trading_day('20260318')
            >>> print(is_trading)  # True
        """
        query = """
            SELECT is_open
            FROM trade_cal
            WHERE cal_date = %s
              AND exchange = %s
        """

        try:
            result = self.execute_query(query, (check_date, exchange))
            if result:
                return bool(result[0][0])
            return False

        except Exception as e:
            logger.error(f"判断交易日失败: {e}")
            raise QueryError(
                "判断交易日失败",
                error_code="IS_TRADING_DAY_CHECK_FAILED",
                reason=str(e)
            )

    def get_trading_days_between(
        self,
        start_date: str,
        end_date: str,
        exchange: str = 'SSE'
    ) -> List[str]:
        """
        获取日期范围内的所有交易日

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            exchange: 交易所代码

        Returns:
            交易日列表

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> days = repo.get_trading_days_between('20260301', '20260331')
            >>> len(days)  # 20
        """
        query = """
            SELECT cal_date
            FROM trade_cal
            WHERE is_open = 1
              AND exchange = %s
              AND cal_date >= %s
              AND cal_date <= %s
            ORDER BY cal_date ASC
        """

        try:
            result = self.execute_query(query, (exchange, start_date, end_date))
            return [row[0] for row in result]

        except Exception as e:
            logger.error(f"查询交易日列表失败: {e}")
            raise QueryError(
                "查询交易日列表失败",
                error_code="TRADING_DAYS_LIST_QUERY_FAILED",
                reason=str(e)
            )

    def get_recent_n_trading_days(
        self,
        n: int = 30,
        reference_date: Optional[str] = None,
        exchange: str = 'SSE'
    ) -> List[str]:
        """
        获取最近 N 个交易日

        Args:
            n: 交易日数量
            reference_date: 参考日期，格式：YYYYMMDD（默认为今天）
            exchange: 交易所代码

        Returns:
            最近 N 个交易日列表（倒序）

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> recent_days = repo.get_recent_n_trading_days(30)
            >>> len(recent_days)  # 30
        """
        if reference_date is None:
            reference_date = datetime.now().strftime("%Y%m%d")

        query = """
            SELECT cal_date
            FROM trade_cal
            WHERE is_open = 1
              AND exchange = %s
              AND cal_date <= %s
            ORDER BY cal_date DESC
            LIMIT %s
        """

        try:
            result = self.execute_query(query, (exchange, reference_date, n))
            return [row[0] for row in result]

        except Exception as e:
            logger.error(f"查询最近N个交易日失败: {e}")
            raise QueryError(
                "查询最近N个交易日失败",
                error_code="RECENT_N_DAYS_QUERY_FAILED",
                reason=str(e)
            )

    def get_calendar_by_date_range(
        self,
        start_date: str,
        end_date: str,
        exchange: str = 'SSE'
    ) -> List[Dict]:
        """
        获取日期范围内的完整日历信息（包含非交易日）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            exchange: 交易所代码

        Returns:
            日历信息列表

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> calendar = repo.get_calendar_by_date_range('20260301', '20260331')
        """
        query = """
            SELECT exchange, cal_date, is_open, pretrade_date
            FROM trade_cal
            WHERE exchange = %s
              AND cal_date >= %s
              AND cal_date <= %s
            ORDER BY cal_date ASC
        """

        try:
            result = self.execute_query(query, (exchange, start_date, end_date))
            return [
                {
                    "exchange": row[0],
                    "cal_date": row[1],
                    "is_open": bool(row[2]),
                    "pretrade_date": row[3]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"查询日历信息失败: {e}")
            raise QueryError(
                "查询日历信息失败",
                error_code="CALENDAR_RANGE_QUERY_FAILED",
                reason=str(e)
            )

    def get_latest_data_date_from_tables(
        self,
        table_names: List[str] = None
    ) -> Optional[str]:
        """
        从多个表中查找最新的数据日期

        Args:
            table_names: 表名列表（默认查询常用表）

        Returns:
            最新数据日期，格式：YYYYMMDD

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> latest = repo.get_latest_data_date_from_tables()
            >>> print(latest)  # '20260318'
        """
        if table_names is None:
            table_names = [
                "stock_daily",
                "daily_basic",
                "moneyflow",
                "hk_hold"
            ]

        latest_dates = []

        for table_name in table_names:
            query = f"SELECT MAX(trade_date) FROM {table_name}"

            try:
                result = self.execute_query(query)
                if result and result[0][0]:
                    latest_dates.append(result[0][0])
            except Exception as e:
                # 某个表可能不存在，忽略错误
                logger.debug(f"查询表 {table_name} 失败（可能不存在）: {e}")
                continue

        if latest_dates:
            return max(latest_dates)

        return None

    def get_calendar_paged(
        self,
        exchange: str = 'SSE',
        start_date: str = '19900101',
        end_date: str = '29991231',
        is_open: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict]:
        """
        分页查询交易日历数据

        Args:
            exchange: 交易所代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            is_open: 是否交易 '0'休市 '1'交易（可选）
            limit: 每页记录数
            offset: 偏移量

        Returns:
            日历数据列表

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> items = repo.get_calendar_paged('SSE', '20260101', '20261231')
        """
        conditions = [
            "exchange = %s",
            "cal_date >= %s",
            "cal_date <= %s"
        ]
        params = [exchange, start_date, end_date]

        if is_open is not None:
            conditions.append("is_open = %s")
            params.append(int(is_open))

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT exchange, cal_date, is_open, pretrade_date
            FROM trade_cal
            WHERE {where_clause}
            ORDER BY cal_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])

        try:
            result = self.execute_query(query, tuple(params))
            return [
                {
                    "exchange": row[0],
                    "cal_date": row[1],
                    "is_open": int(row[2]) if row[2] is not None else 0,
                    "pretrade_date": row[3]
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"分页查询交易日历失败: {e}")
            raise QueryError(
                "分页查询交易日历失败",
                error_code="CALENDAR_PAGED_QUERY_FAILED",
                reason=str(e)
            )

    def get_calendar_count(
        self,
        exchange: str = 'SSE',
        start_date: str = '19900101',
        end_date: str = '29991231',
        is_open: Optional[str] = None
    ) -> int:
        """
        统计交易日历记录数

        Args:
            exchange: 交易所代码
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            is_open: 是否交易 '0'休市 '1'交易（可选）

        Returns:
            记录数

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> count = repo.get_calendar_count('SSE', '20260101', '20261231')
        """
        conditions = [
            "exchange = %s",
            "cal_date >= %s",
            "cal_date <= %s"
        ]
        params = [exchange, start_date, end_date]

        if is_open is not None:
            conditions.append("is_open = %s")
            params.append(int(is_open))

        where_clause = " AND ".join(conditions)
        query = f"SELECT COUNT(*) FROM trade_cal WHERE {where_clause}"

        try:
            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"统计交易日历记录数失败: {e}")
            raise QueryError(
                "统计交易日历记录数失败",
                error_code="CALENDAR_COUNT_QUERY_FAILED",
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def bulk_upsert_calendar(self, df: pd.DataFrame, exchange: str = 'SSE') -> int:
        """
        批量插入/更新交易日历数据

        Args:
            df: 交易日历数据（包含 cal_date, is_open, pretrade_date 列）
            exchange: 交易所代码

        Returns:
            影响的行数

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'cal_date': ['20260318', '20260319'],
            ...     'is_open': [1, 1],
            ...     'pretrade_date': ['20260317', '20260318']
            ... })
            >>> count = repo.bulk_upsert_calendar(df)
        """
        if df.empty:
            logger.warning("数据为空，跳过插入")
            return 0

        # 确保必需列存在
        required_cols = ['cal_date', 'is_open']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需列: {missing_cols}")

        query = """
            INSERT INTO trade_cal (exchange, cal_date, is_open, pretrade_date)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (exchange, cal_date)
            DO UPDATE SET
                is_open = EXCLUDED.is_open,
                pretrade_date = EXCLUDED.pretrade_date
        """

        try:
            records = []
            for _, row in df.iterrows():
                records.append((
                    exchange,
                    row['cal_date'],
                    int(row['is_open']),
                    row.get('pretrade_date', None)
                ))

            rows_affected = self.execute_batch(query, records)
            logger.info(f"批量插入交易日历数据: {rows_affected} 行")
            return rows_affected

        except Exception as e:
            logger.error(f"批量插入交易日历失败: {e}")
            raise DatabaseError(
                "批量插入交易日历失败",
                error_code="CALENDAR_BULK_UPSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        exchange: str = 'SSE'
    ) -> int:
        """
        删除指定日期范围的日历数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            exchange: 交易所代码

        Returns:
            删除的行数

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> count = repo.delete_by_date_range('20260101', '20260131')
        """
        query = """
            DELETE FROM trade_cal
            WHERE exchange = %s
              AND cal_date >= %s
              AND cal_date <= %s
        """

        try:
            rows_affected = self.execute_update(query, (exchange, start_date, end_date))
            logger.info(f"删除交易日历数据: {rows_affected} 行")
            return rows_affected

        except Exception as e:
            logger.error(f"删除交易日历数据失败: {e}")
            raise DatabaseError(
                "删除交易日历数据失败",
                error_code="CALENDAR_DELETE_FAILED",
                reason=str(e)
            )

    # ==================== 辅助方法 ====================

    def calculate_fallback_trading_day(self, reference_date: Optional[datetime] = None) -> str:
        """
        基于日期规则计算回退交易日（当数据库无数据时使用）

        Args:
            reference_date: 参考日期（默认为今天）

        Returns:
            回退交易日，格式：YYYYMMDD

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> fallback = repo.calculate_fallback_trading_day()
        """
        if reference_date is None:
            reference_date = datetime.now()

        # 如果是周末，回退到上周五
        if reference_date.weekday() == 5:  # 周六
            reference_date = reference_date - timedelta(days=1)
        elif reference_date.weekday() == 6:  # 周日
            reference_date = reference_date - timedelta(days=2)

        # 如果是工作日但时间早于15:30（市场收盘时间），使用前一个交易日
        if reference_date.weekday() < 5:  # 周一到周五
            if reference_date.hour < 15 or (reference_date.hour == 15 and reference_date.minute < 30):
                # 回退到前一个交易日
                reference_date = reference_date - timedelta(days=1)
                # 如果回退后是周末，继续回退到周五
                if reference_date.weekday() == 5:  # 周六
                    reference_date = reference_date - timedelta(days=1)
                elif reference_date.weekday() == 6:  # 周日
                    reference_date = reference_date - timedelta(days=2)

        result = reference_date.strftime("%Y%m%d")
        logger.info(f"基于规则计算的回退交易日: {result}")
        return result

    def get_statistics(self, year: Optional[int] = None, exchange: str = 'SSE') -> Dict:
        """
        获取交易日历统计信息

        Args:
            year: 年份（默认为当前年份）
            exchange: 交易所代码

        Returns:
            统计信息字典

        Examples:
            >>> repo = TradingCalendarRepository()
            >>> stats = repo.get_statistics(year=2026)
            >>> print(stats['trading_days'])  # 242
        """
        if year is None:
            year = datetime.now().year

        start_date = f"{year}0101"
        end_date = f"{year}1231"

        query = """
            SELECT
                COUNT(*) as total_days,
                COUNT(CASE WHEN is_open = 1 THEN 1 END) as trading_days,
                COUNT(CASE WHEN is_open = 0 THEN 1 END) as non_trading_days
            FROM trade_cal
            WHERE exchange = %s
              AND cal_date >= %s
              AND cal_date <= %s
        """

        try:
            result = self.execute_query(query, (exchange, start_date, end_date))
            if not result:
                return {
                    "year": year,
                    "total_days": 0,
                    "trading_days": 0,
                    "non_trading_days": 0,
                    "trading_day_ratio": 0.0
                }

            row = result[0]
            total = row[0] or 0
            trading = row[1] or 0
            non_trading = row[2] or 0

            return {
                "year": year,
                "total_days": total,
                "trading_days": trading,
                "non_trading_days": non_trading,
                "trading_day_ratio": round((trading / total * 100), 2) if total > 0 else 0.0
            }

        except Exception as e:
            logger.error(f"获取交易日历统计失败: {e}")
            raise QueryError(
                "获取交易日历统计失败",
                error_code="CALENDAR_STATISTICS_QUERY_FAILED",
                reason=str(e)
            )
