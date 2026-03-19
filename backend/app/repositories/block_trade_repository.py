"""
大宗交易数据访问层

提供大宗交易数据的增删改查操作，支持按日期、股票代码查询。

数据表: block_trade
数据源: Tushare pro.block_trade()
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class BlockTradeRepository(BaseRepository):
    """
    大宗交易数据访问层

    职责：
    - 按日期和股票代码查询大宗交易数据
    - 批量插入/更新大宗交易数据
    - 获取大宗交易统计信息
    - 查询成交额排名
    """

    TABLE_NAME = "block_trade"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ BlockTradeRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按交易日期和股票代码查询大宗交易数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）
            limit: 返回记录数

        Returns:
            大宗交易数据列表

        Examples:
            >>> repo = BlockTradeRepository()
            >>> data = repo.get_by_date('20240115')
            >>> data = repo.get_by_date('20240115', ts_code='000001.SZ')
        """
        try:
            conditions = []
            params = []

            if trade_date:
                conditions.append("trade_date = %s")
                params.append(trade_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    id, ts_code, trade_date, price, vol, amount, buyer, seller,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY amount DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "id": row[0],
                    "ts_code": row[1],
                    "trade_date": row[2],
                    "price": float(row[3]) if row[3] is not None else None,
                    "vol": float(row[4]) if row[4] is not None else 0,
                    "amount": float(row[5]) if row[5] is not None else 0,
                    "buyer": row[6],
                    "seller": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "updated_at": row[9].isoformat() if row[9] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询大宗交易数据失败: {e}")
            raise QueryError(
                "大宗交易数据查询失败",
                error_code="BLOCK_TRADE_QUERY_FAILED",
                trade_date=trade_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_by_code_and_date_range(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询大宗交易数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数

        Returns:
            大宗交易数据列表
        """
        try:
            conditions = ["ts_code = %s"]
            params = [ts_code]

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    id, ts_code, trade_date, price, vol, amount, buyer, seller,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, amount DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "id": row[0],
                    "ts_code": row[1],
                    "trade_date": row[2],
                    "price": float(row[3]) if row[3] is not None else None,
                    "vol": float(row[4]) if row[4] is not None else 0,
                    "amount": float(row[5]) if row[5] is not None else 0,
                    "buyer": row[6],
                    "seller": row[7],
                    "created_at": row[8].isoformat() if row[8] else None,
                    "updated_at": row[9].isoformat() if row[9] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询大宗交易数据失败: {e}")
            raise QueryError(
                "大宗交易数据查询失败",
                error_code="BLOCK_TRADE_QUERY_FAILED",
                ts_code=ts_code,
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
        获取大宗交易统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典
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
                    COUNT(DISTINCT ts_code) as stock_count,
                    MAX(trade_date) as latest_date,
                    COUNT(*) as total_records,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and result[0]:
                row = result[0]
                return {
                    "stock_count": row[0] or 0,
                    "latest_date": row[1] or "",
                    "total_records": row[2] or 0,
                    "total_amount": float(row[3]) if row[3] else 0,
                    "avg_amount": float(row[4]) if row[4] else 0,
                    "max_amount": float(row[5]) if row[5] else 0
                }

            return {
                "stock_count": 0,
                "latest_date": "",
                "total_records": 0,
                "total_amount": 0,
                "avg_amount": 0,
                "max_amount": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取大宗交易统计失败: {e}")
            raise QueryError(
                "大宗交易统计查询失败",
                error_code="BLOCK_TRADE_STATS_FAILED",
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

    def bulk_insert(self, df: pd.DataFrame) -> int:
        """
        批量插入大宗交易数据

        注意：大宗交易数据一般不需要更新，只插入新数据

        Args:
            df: 大宗交易数据 DataFrame，必须包含相应列

        Returns:
            影响的行数

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败
        """
        if df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 验证必需列
            required_columns = {'trade_date', 'ts_code'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"大宗交易 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = ['ts_code', 'trade_date', 'price', 'vol', 'amount', 'buyer', 'seller']

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

            # 构建SQL（使用ON CONFLICT DO NOTHING避免重复插入）
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (trade_date, ts_code, price, vol)
                DO NOTHING
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

                logger.info(f"✓ 批量插入大宗交易数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入大宗交易数据失败: {e}")
            raise DatabaseError(
                "大宗交易数据批量插入失败",
                error_code="BLOCK_TRADE_BULK_INSERT_FAILED",
                count=len(df),
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围的大宗交易数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的行数
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM {self.TABLE_NAME} WHERE {where_clause}"

            count = self.execute_update(query, tuple(params))
            logger.info(f"✓ 删除大宗交易数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除大宗交易数据失败: {e}")
            raise DatabaseError(
                "大宗交易数据删除失败",
                error_code="BLOCK_TRADE_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )
