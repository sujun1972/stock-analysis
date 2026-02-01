#!/usr/bin/env python3
"""
数据查询管理器

负责所有数据的查询和读取操作。
"""

import pandas as pd
import psycopg2
import logging
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime, timedelta

# 导入异常类
try:
    from ..exceptions import DatabaseError
except ImportError:
    from src.exceptions import DatabaseError

if TYPE_CHECKING:
    from .connection_pool_manager import ConnectionPoolManager

logger = logging.getLogger(__name__)


class DataQueryManager:
    """
    数据查询管理器

    职责：
    - 处理所有数据的查询操作
    - 数据完整性检查
    - 数据加载和格式化
    """

    def __init__(self, pool_manager: 'ConnectionPoolManager'):
        """
        初始化数据查询管理器

        Args:
            pool_manager: 连接池管理器实例
        """
        self.pool_manager = pool_manager

    def load_daily_data(self, stock_code: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        从数据库加载股票日线数据

        Args:
            stock_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            包含日线数据的DataFrame
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()

            query = """
                SELECT date, open, high, low, close, volume, amount,
                       amplitude, pct_change, change, turnover
                FROM stock_daily
                WHERE code = %s
            """
            params = [stock_code]

            if start_date:
                query += " AND date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND date <= %s"
                params.append(end_date)

            query += " ORDER BY date ASC"

            # 抑制 pandas 关于 DBAPI2 连接的警告（我们知道使用 psycopg2）
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
                df = pd.read_sql_query(query, conn, params=params, index_col='date', parse_dates=['date'])

            # 确保数值列是正确的类型
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'amount',
                              'amplitude', 'pct_change', 'change', 'turnover']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            logger.info(f"✓ 加载 {stock_code} 数据: {len(df)} 条记录")
            return df

        except psycopg2.OperationalError as e:
            # 连接错误
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                operation="load_daily_data",
                stock_code=stock_code,
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                operation="load_daily_data",
                stock_code=stock_code,
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常，直接向上传播
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(f"❌ 加载 {stock_code} 数据失败(未预期异常): {e}")
            raise DatabaseError(
                f"加载日线数据失败: {str(e)}",
                error_code="DB_QUERY_FAILED",
                operation="load_daily_data",
                stock_code=stock_code
            ) from e

        finally:
            if conn:
                self.pool_manager.release_connection(conn)

    def get_stock_list(self, market: Optional[str] = None,
                      status: str = '正常') -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型（可选）
            status: 股票状态（默认为正常）

        Returns:
            股票列表DataFrame
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()

            query = "SELECT * FROM stock_info WHERE status = %s"
            params = [status]

            if market:
                query += " AND market = %s"
                params.append(market)

            query += " ORDER BY code"

            df = pd.read_sql_query(query, conn, params=params)
            logger.info(f"✓ 获取股票列表: {len(df)} 只股票")
            return df

        except psycopg2.OperationalError as e:
            # 连接错误
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                operation="get_stock_list",
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                operation="get_stock_list",
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常，直接向上传播
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(f"❌ 获取股票列表失败(未预期异常): {e}")
            raise DatabaseError(
                f"获取股票列表失败: {str(e)}",
                error_code="DB_QUERY_FAILED",
                operation="get_stock_list"
            ) from e

        finally:
            if conn:
                self.pool_manager.release_connection(conn)

    def get_oldest_realtime_stocks(self, limit: int = 100) -> List[str]:
        """
        获取更新时间最早的N只股票代码（用于渐进式更新实时行情）

        Args:
            limit: 返回的股票数量

        Returns:
            股票代码列表
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询updated_at最早的股票
            query = """
                SELECT s.code
                FROM stock_basic s
                LEFT JOIN stock_realtime r ON s.code = r.code
                WHERE s.status = '正常'
                ORDER BY r.updated_at NULLS FIRST
                LIMIT %s
            """

            cursor.execute(query, (limit,))
            codes = [row[0] for row in cursor.fetchall()]

            logger.info(f"✓ 获取 {len(codes)} 只最早更新的股票代码")
            return codes

        except psycopg2.OperationalError as e:
            # 连接错误
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                operation="get_oldest_realtime_stocks",
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                operation="get_oldest_realtime_stocks",
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常，直接向上传播
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(f"❌ 获取最旧实时行情股票失败(未预期异常): {e}")
            raise DatabaseError(
                f"获取最旧实时行情股票失败: {str(e)}",
                error_code="DB_QUERY_FAILED",
                operation="get_oldest_realtime_stocks"
            ) from e

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    def check_daily_data_completeness(self, code: str, start_date: str, end_date: str,
                                     min_expected_days: int = None) -> Dict[str, Any]:
        """
        检查股票的日线数据是否完整

        Args:
            code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            min_expected_days: 最小期望交易日数量（可选，如果不提供则不检查）

        Returns:
            Dict包含：
                - has_data: bool, 是否有数据
                - is_complete: bool, 数据是否完整（如果提供了min_expected_days）
                - record_count: int, 实际记录数
                - earliest_date: str, 最早日期
                - latest_date: str, 最新日期
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 转换日期格式 YYYYMMDD -> YYYY-MM-DD
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

            query = """
                SELECT
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date
                FROM stock_daily
                WHERE code = %s
                    AND date >= %s
                    AND date <= %s
            """

            cursor.execute(query, (code, start_date_formatted, end_date_formatted))
            result = cursor.fetchone()

            record_count = result[0] if result else 0
            earliest_date = result[1] if result and result[1] else None
            latest_date = result[2] if result and result[2] else None

            has_data = record_count > 0

            # 如果提供了最小期望天数，检查是否完整
            is_complete = False
            if min_expected_days is not None:
                # 数据被认为是完整的，如果：
                # 1. 记录数达到最小期望的80%以上（考虑节假日等）
                # 2. 最新日期接近结束日期（在30天内）
                if has_data and record_count >= min_expected_days * 0.8:
                    if latest_date:
                        latest_dt = datetime.strptime(str(latest_date), '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date_formatted, '%Y-%m-%d')
                        days_diff = (end_dt - latest_dt).days
                        is_complete = days_diff <= 30

            cursor.close()

            return {
                'has_data': has_data,
                'is_complete': is_complete,
                'record_count': record_count,
                'earliest_date': str(earliest_date) if earliest_date else None,
                'latest_date': str(latest_date) if latest_date else None
            }

        except psycopg2.OperationalError as e:
            # 连接错误 - 返回默认值以支持容错
            logger.warning(f"数据库连接错误(容错模式): {e}")
            return {
                'has_data': False,
                'is_complete': False,
                'record_count': 0,
                'earliest_date': None,
                'latest_date': None
            }

        except psycopg2.ProgrammingError as e:
            # SQL语法错误 - 返回默认值以支持容错
            logger.warning(f"SQL语法错误(容错模式): {e}")
            return {
                'has_data': False,
                'is_complete': False,
                'record_count': 0,
                'earliest_date': None,
                'latest_date': None
            }

        except Exception as e:
            # 未预期的异常 - 返回默认值以支持容错
            logger.error(f"❌ 检查 {code} 数据完整性失败(未预期异常): {e}")
            return {
                'has_data': False,
                'is_complete': False,
                'record_count': 0,
                'earliest_date': None,
                'latest_date': None
            }

        finally:
            if conn:
                self.pool_manager.release_connection(conn)

    def load_minute_data(self, code: str, period: str, trade_date: str) -> pd.DataFrame:
        """
        从数据库加载分时数据

        Args:
            code: 股票代码
            period: 分时周期
            trade_date: 交易日期

        Returns:
            包含分时数据的DataFrame
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()

            query = """
                SELECT trade_time, open, high, low, close, volume, amount,
                       pct_change, change_amount
                FROM stock_minute
                WHERE code = %s AND period = %s AND DATE(trade_time) = %s
                ORDER BY trade_time ASC
            """

            df = pd.read_sql_query(query, conn, params=(code, period, trade_date))
            logger.info(f"✓ 加载 {code} {period}分钟数据: {len(df)} 条记录")
            return df

        except psycopg2.OperationalError as e:
            # 连接错误
            logger.error(f"数据库连接错误: {e}")
            raise DatabaseError(
                "数据库连接失败",
                error_code="DB_CONNECTION_ERROR",
                operation="load_minute_data",
                stock_code=code,
                period=period,
                trade_date=trade_date,
                error_detail=str(e)
            ) from e

        except psycopg2.ProgrammingError as e:
            # SQL语法错误
            logger.error(f"SQL语法错误: {e}")
            raise DatabaseError(
                "SQL语句错误",
                error_code="DB_SYNTAX_ERROR",
                operation="load_minute_data",
                stock_code=code,
                period=period,
                trade_date=trade_date,
                error_detail=str(e)
            ) from e

        except DatabaseError:
            # 已知的业务异常，直接向上传播
            raise

        except Exception as e:
            # 未预期的异常
            logger.error(f"❌ 加载分时数据失败(未预期异常): {e}")
            raise DatabaseError(
                f"加载分时数据失败: {str(e)}",
                error_code="DB_QUERY_FAILED",
                operation="load_minute_data",
                stock_code=code,
                period=period,
                trade_date=trade_date
            ) from e

        finally:
            if conn:
                self.pool_manager.release_connection(conn)

    def check_minute_data_complete(self, code: str, period: str, trade_date: str) -> dict:
        """
        检查分时数据是否完整

        Returns:
            {
                'is_complete': bool,
                'record_count': int,
                'expected_count': int,
                'completeness': float  # 完整度百分比
            }
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询元数据
            cursor.execute("""
                SELECT is_complete, record_count, expected_count
                FROM stock_minute_meta
                WHERE code = %s AND trade_date = %s AND period = %s
            """, (code, trade_date, period))

            result = cursor.fetchone()

            if result:
                is_complete, record_count, expected_count = result
                completeness = (record_count / expected_count * 100) if expected_count > 0 else 0
            else:
                # 如果元数据不存在，直接查询数据表
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM stock_minute
                    WHERE code = %s AND DATE(trade_time) = %s AND period = %s
                """, (code, trade_date, period))

                record_count = cursor.fetchone()[0]
                expected_count = self._get_expected_minute_count(period)
                is_complete = record_count >= expected_count * 0.95
                completeness = (record_count / expected_count * 100) if expected_count > 0 else 0

            return {
                'is_complete': is_complete,
                'record_count': record_count,
                'expected_count': expected_count,
                'completeness': round(completeness, 2)
            }

        except psycopg2.OperationalError as e:
            # 连接错误 - 返回默认值以支持容错
            logger.warning(f"数据库连接错误(容错模式): {e}")
            return {
                'is_complete': False,
                'record_count': 0,
                'expected_count': 0,
                'completeness': 0
            }

        except psycopg2.ProgrammingError as e:
            # SQL语法错误 - 返回默认值以支持容错
            logger.warning(f"SQL语法错误(容错模式): {e}")
            return {
                'is_complete': False,
                'record_count': 0,
                'expected_count': 0,
                'completeness': 0
            }

        except Exception as e:
            # 未预期的异常 - 返回默认值以支持容错
            logger.error(f"❌ 检查数据完整性失败(未预期异常): {e}")
            return {
                'is_complete': False,
                'record_count': 0,
                'expected_count': 0,
                'completeness': 0
            }

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    def is_trading_day(self, trade_date: str) -> bool:
        """检查是否为交易日"""
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT is_trading_day
                FROM trading_calendar
                WHERE trade_date = %s
            """, (trade_date,))

            result = cursor.fetchone()

            if result:
                return result[0]
            else:
                # 如果日历表中没有数据，简单判断：周一到周五为交易日
                date_obj = datetime.strptime(trade_date, '%Y-%m-%d')
                return date_obj.weekday() < 5  # 0-4 为周一到周五

        except psycopg2.OperationalError as e:
            # 连接错误 - 返回默认值以支持容错
            logger.warning(f"数据库连接错误(容错模式): {e}")
            return True  # 默认为交易日

        except psycopg2.ProgrammingError as e:
            # SQL语法错误 - 返回默认值以支持容错
            logger.warning(f"SQL语法错误(容错模式): {e}")
            return True  # 默认为交易日

        except Exception as e:
            # 未预期的异常 - 返回默认值以支持容错
            logger.warning(f"检查交易日失败(未预期异常): {e}")
            return True  # 默认为交易日

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    @staticmethod
    def _get_expected_minute_count(period: str) -> int:
        """获取期望的分时记录数"""
        # A股交易时间：9:30-11:30 (120分钟) + 13:00-15:00 (120分钟) = 240分钟
        total_minutes = 240
        period_map = {
            '1': total_minutes,      # 240条
            '5': total_minutes // 5,  # 48条
            '15': total_minutes // 15,  # 16条
            '30': total_minutes // 30,  # 8条
            '60': total_minutes // 60   # 4条
        }
        return period_map.get(period, 48)
