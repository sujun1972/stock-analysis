"""
北向资金持股数据访问层

提供北向资金持股数据的增删改查操作，支持按日期、交易所查询，
以及批量插入、统计分析等功能。

数据表: hk_hold
数据源: Tushare pro.hk_hold()
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class HkHoldRepository(BaseRepository):
    """
    北向资金持股数据访问层

    职责：
    - 按日期和交易所查询持股数据
    - 批量插入/更新持股数据
    - 获取持股统计信息
    - 查询持股比例排名
    """

    TABLE_NAME = "hk_hold"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ HkHoldRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date(
        self,
        trade_date: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按日期和交易所查询持股数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            exchange: 交易所（SH-沪股通，SZ-深股通）（可选）
            limit: 返回记录数

        Returns:
            持股数据列表

        Examples:
            >>> repo = HkHoldRepository()
            >>> data = repo.get_by_date('20240115')
            >>> data = repo.get_by_date('20240115', exchange='SH')
        """
        try:
            conditions = []
            params = []

            if trade_date:
                conditions.append("trade_date = %s")
                params.append(trade_date)
            if exchange:
                conditions.append("exchange = %s")
                params.append(exchange)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    code, trade_date, ts_code, name, vol, ratio, exchange,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY ratio DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "code": row[0],
                    "trade_date": row[1],
                    "ts_code": row[2],
                    "name": row[3],
                    "vol": float(row[4]) if row[4] is not None else 0,
                    "ratio": float(row[5]) if row[5] is not None else 0,
                    "exchange": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询北向资金持股数据失败: {e}")
            raise QueryError(
                "北向资金持股数据查询失败",
                error_code="HK_HOLD_QUERY_FAILED",
                trade_date=trade_date,
                exchange=exchange,
                reason=str(e)
            )

    def get_by_code(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询持股数据

        Args:
            code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数

        Returns:
            持股数据列表

        Examples:
            >>> repo = HkHoldRepository()
            >>> data = repo.get_by_code('600519', '20240101', '20240131')
        """
        try:
            conditions = ["code = %s"]
            params = [code]

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    code, trade_date, ts_code, name, vol, ratio, exchange,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "code": row[0],
                    "trade_date": row[1],
                    "ts_code": row[2],
                    "name": row[3],
                    "vol": float(row[4]) if row[4] is not None else 0,
                    "ratio": float(row[5]) if row[5] is not None else 0,
                    "exchange": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询股票持股数据失败: {e}")
            raise QueryError(
                "股票持股数据查询失败",
                error_code="HK_HOLD_CODE_QUERY_FAILED",
                code=code,
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取持股统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"股票数量: {stats['stock_count']}")
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(DISTINCT code) as stock_count,
                    MAX(trade_date) as latest_date,
                    COUNT(*) as total_records
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and result[0]:
                row = result[0]
                return {
                    "stock_count": row[0] or 0,
                    "latest_date": row[1] or "",
                    "total_records": row[2] or 0
                }

            return {
                "stock_count": 0,
                "latest_date": "",
                "total_records": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取持股统计失败: {e}")
            raise QueryError(
                "持股统计查询失败",
                error_code="HK_HOLD_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（格式：YYYYMMDD），如果没有数据则返回None
        """
        try:
            query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
            result = self.execute_query(query)
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新持股数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 持股数据 DataFrame，必须包含 trade_date, code 等列

        Returns:
            影响的行数

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败

        Examples:
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
            >>> print(f"插入/更新了 {count} 条记录")
        """
        if df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 验证必需列
            required_columns = {'trade_date', 'code'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"北向资金持股 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = ['code', 'trade_date', 'ts_code', 'name', 'vol', 'ratio', 'exchange']

            # 确保所有列都存在（缺失的填充为NULL）
            for col in columns:
                if col not in df.columns:
                    df[col] = None

            # 准备数据
            values = []
            for _, row in df.iterrows():
                values.append(tuple(row[col] for col in columns))

            if not values:
                return 0

            # 构建SQL - UPSERT语义
            # 主键: (code, trade_date, exchange) - 必须与数据库表定义一致
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            # 排除主键字段，只更新非主键列
            update_columns = ','.join([
                f"{col} = EXCLUDED.{col}"
                for col in columns if col not in ['code', 'trade_date', 'exchange']
            ])

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (code, trade_date, exchange)
                DO UPDATE SET
                    {update_columns},
                    updated_at = NOW()
            """

            # 批量执行
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                affected_rows = 0
                for value_tuple in values:
                    cursor.execute(query, value_tuple)
                    affected_rows += cursor.rowcount
                conn.commit()
                cursor.close()

                logger.info(f"✓ 批量插入/更新北向资金持股数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入北向资金持股数据失败: {e}")
            raise DatabaseError(
                "北向资金持股数据批量插入失败",
                error_code="HK_HOLD_BULK_INSERT_FAILED",
                count=len(df),
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围的持股数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            code: 股票代码（可选，不指定则删除所有股票）

        Returns:
            删除的行数
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if code:
                conditions.append("code = %s")
                params.append(code)

            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM {self.TABLE_NAME} WHERE {where_clause}"

            count = self.execute_update(query, tuple(params))
            logger.info(f"✓ 删除北向资金持股数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除北向资金持股数据失败: {e}")
            raise DatabaseError(
                "北向资金持股数据删除失败",
                error_code="HK_HOLD_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(self, trade_date: str, code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            code: 股票代码（可选）

        Returns:
            是否存在
        """
        try:
            if code:
                return self.exists(
                    self.TABLE_NAME,
                    "trade_date = %s AND code = %s",
                    (trade_date, code)
                )
            else:
                return self.exists(
                    self.TABLE_NAME,
                    "trade_date = %s",
                    (trade_date,)
                )
        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            记录数
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else None

            return self.count(
                self.TABLE_NAME,
                where_clause,
                tuple(params) if params else None
            )
        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0
