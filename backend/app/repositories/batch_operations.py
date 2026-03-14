"""
批量操作优化模块

提供高性能的数据库批量操作功能:
- 批量插入优化 (execute_batch, execute_values)
- 批量查询优化 (WHERE IN)
- 批量更新/删除
- 事务管理
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError
from psycopg2.extras import execute_batch, execute_values
from src.database.db_manager import DatabaseManager

from app.core.exceptions import DatabaseError


class BatchOperations:
    """
    批量操作优化类

    提供高性能的数据库批量操作功能
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化批量操作管理器

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()

    # ==================== 批量插入优化 ====================

    def bulk_insert_daily_data(
        self,
        data_list: List[Tuple],
        batch_size: int = 1000
    ) -> int:
        """
        批量插入日线数据（高性能）

        Args:
            data_list: 数据列表 [(code, date, open, high, low, close, volume, ...), ...]
            batch_size: 批次大小（默认1000）

        Returns:
            插入的记录数

        Raises:
            DatabaseError: 数据库操作失败
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # SQL 语句
            insert_sql = """
                INSERT INTO daily_data
                (code, date, open, high, low, close, volume, amount,
                 amplitude, pct_change, change, turnover)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    amount = EXCLUDED.amount,
                    amplitude = EXCLUDED.amplitude,
                    pct_change = EXCLUDED.pct_change,
                    change = EXCLUDED.change,
                    turnover = EXCLUDED.turnover,
                    updated_at = CURRENT_TIMESTAMP
            """

            # 使用 execute_batch 批量插入（比 executemany 更快）
            execute_batch(cursor, insert_sql, data_list, page_size=batch_size)

            # 提交事务
            conn.commit()

            count = len(data_list)
            logger.debug(f"批量插入日线数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"批量插入日线数据失败: {e}")
            raise DatabaseError(
                "批量插入日线数据失败",
                error_code="BULK_INSERT_FAILED",
                count=len(data_list) if data_list else 0,
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    def bulk_insert_daily_data_from_dataframe(
        self,
        df: pd.DataFrame,
        code: str,
        batch_size: int = 1000
    ) -> int:
        """
        从 DataFrame 批量插入日线数据

        Args:
            df: 日线数据 DataFrame（索引为日期）
            code: 股票代码
            batch_size: 批次大小

        Returns:
            插入的记录数
        """
        try:
            # 重置索引以获取日期列
            df_reset = df.reset_index()

            # 准备数据列表
            data_list = []
            for _, row in df_reset.iterrows():
                data_list.append((
                    code,
                    row.get('date'),
                    float(row.get('open', 0)),
                    float(row.get('high', 0)),
                    float(row.get('low', 0)),
                    float(row.get('close', 0)),
                    int(row.get('volume', 0)),
                    float(row.get('amount', 0)),
                    float(row.get('amplitude', 0)),
                    float(row.get('pct_change', 0)),
                    float(row.get('change', 0)),
                    float(row.get('turnover', 0))
                ))

            return self.bulk_insert_daily_data(data_list, batch_size)

        except Exception as e:
            logger.error(f"从 DataFrame 批量插入失败: {e}")
            raise DatabaseError(
                f"股票 {code} 批量插入失败",
                error_code="BULK_INSERT_FROM_DF_FAILED",
                stock_code=code,
                reason=str(e)
            )

    def bulk_insert_stock_list(
        self,
        stock_list: List[Tuple[str, str, str]],
        batch_size: int = 500
    ) -> int:
        """
        批量插入股票列表

        Args:
            stock_list: 股票列表 [(code, name, market), ...]
            batch_size: 批次大小

        Returns:
            插入的记录数
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            insert_sql = """
                INSERT INTO stock_list (code, name, market)
                VALUES %s
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    market = EXCLUDED.market,
                    updated_at = CURRENT_TIMESTAMP
            """

            # 使用 execute_values（最快）
            execute_values(
                cursor,
                insert_sql,
                stock_list,
                template="(%s, %s, %s)",
                page_size=batch_size
            )

            conn.commit()

            count = len(stock_list)
            logger.debug(f"批量插入股票列表: {count} 只")
            return count

        except PsycopgDatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"批量插入股票列表失败: {e}")
            raise DatabaseError(
                "批量插入股票列表失败",
                error_code="BULK_INSERT_STOCK_LIST_FAILED",
                count=len(stock_list) if stock_list else 0,
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    # ==================== 批量更新 ====================

    def bulk_update_stock_status(
        self,
        updates: List[Tuple[str, str]],
        batch_size: int = 500
    ) -> int:
        """
        批量更新股票状态

        Args:
            updates: 更新列表 [(status, code), ...]
            batch_size: 批次大小

        Returns:
            更新的记录数
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            update_sql = """
                UPDATE stock_list
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE code = %s
            """

            execute_batch(cursor, update_sql, updates, page_size=batch_size)
            conn.commit()

            count = cursor.rowcount
            logger.debug(f"批量更新股票状态: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"批量更新股票状态失败: {e}")
            raise DatabaseError(
                "批量更新股票状态失败",
                error_code="BULK_UPDATE_STATUS_FAILED",
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    # ==================== 批量查询 ====================

    def bulk_get_latest_dates(
        self,
        codes: List[str]
    ) -> Dict[str, Optional[datetime]]:
        """
        批量获取多只股票的最新数据日期

        Args:
            codes: 股票代码列表

        Returns:
            {code: latest_date} 字典
        """
        try:
            if not codes:
                return {}

            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 使用 WHERE IN 批量查询
            query = """
                SELECT code, MAX(date) as latest_date
                FROM daily_data
                WHERE code = ANY(%s)
                GROUP BY code
            """

            cursor.execute(query, (codes,))
            results = cursor.fetchall()

            # 构建结果字典
            latest_dates = {code: None for code in codes}
            for row in results:
                latest_dates[row[0]] = row[1]

            return latest_dates

        except PsycopgDatabaseError as e:
            logger.error(f"批量获取最新日期失败: {e}")
            raise DatabaseError(
                "批量获取最新日期失败",
                error_code="BULK_GET_LATEST_DATES_FAILED",
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    def bulk_get_data_counts(
        self,
        codes: List[str]
    ) -> Dict[str, int]:
        """
        批量获取多只股票的数据记录数

        Args:
            codes: 股票代码列表

        Returns:
            {code: count} 字典
        """
        try:
            if not codes:
                return {}

            conn = self.db.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT code, COUNT(*) as cnt
                FROM daily_data
                WHERE code = ANY(%s)
                GROUP BY code
            """

            cursor.execute(query, (codes,))
            results = cursor.fetchall()

            # 构建结果字典
            counts = {code: 0 for code in codes}
            for row in results:
                counts[row[0]] = row[1]

            return counts

        except PsycopgDatabaseError as e:
            logger.error(f"批量获取数据记录数失败: {e}")
            raise DatabaseError(
                "批量获取数据记录数失败",
                error_code="BULK_GET_DATA_COUNTS_FAILED",
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    # ==================== 批量删除 ====================

    def bulk_delete_daily_data(
        self,
        codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        批量删除日线数据

        Args:
            codes: 股票代码列表
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            删除的记录数
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            conditions = ["code = ANY(%s)"]
            params = [codes]

            if start_date:
                conditions.append("date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("date <= %s")
                params.append(end_date)

            delete_sql = f"DELETE FROM daily_data WHERE {' AND '.join(conditions)}"
            cursor.execute(delete_sql, params)
            conn.commit()

            count = cursor.rowcount
            logger.debug(f"批量删除日线数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"批量删除日线数据失败: {e}")
            raise DatabaseError(
                "批量删除日线数据失败",
                error_code="BULK_DELETE_FAILED",
                reason=str(e)
            )
        finally:
            if cursor:
                cursor.close()

    # ==================== 事务管理 ====================

    def execute_in_transaction(
        self,
        operations: List[callable]
    ) -> List[Any]:
        """
        在单个事务中执行多个操作

        Args:
            operations: 操作函数列表

        Returns:
            操作结果列表

        Example:
            >>> def op1():
            ...     return batch_ops.bulk_insert_stock_list(stocks)
            >>> def op2():
            ...     return batch_ops.bulk_insert_daily_data(data)
            >>> results = batch_ops.execute_in_transaction([op1, op2])
        """
        conn = None
        try:
            conn = self.db.get_connection()
            conn.autocommit = False

            results = []
            for operation in operations:
                result = operation()
                results.append(result)

            conn.commit()
            logger.debug(f"事务执行成功: {len(operations)} 个操作")
            return results

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"事务执行失败: {e}")
            raise DatabaseError(
                "事务执行失败",
                error_code="TRANSACTION_FAILED",
                operation_count=len(operations),
                reason=str(e)
            )
        finally:
            if conn:
                conn.autocommit = True
