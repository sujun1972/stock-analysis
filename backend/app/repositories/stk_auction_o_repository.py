"""
股票开盘集合竞价数据访问层

提供股票开盘集合竞价数据的增删改查操作，支持按日期、股票代码查询，
以及批量插入、统计分析等功能。

数据表: stk_auction_o
数据源: Tushare pro.stk_auction_o()
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class StkAuctionORepository(BaseRepository):
    """
    股票开盘集合竞价数据访问层

    职责:
    - 按日期和股票代码查询集合竞价数据
    - 批量插入/更新集合竞价数据
    - 获取集合竞价统计信息
    - 查询成交量排名
    """

    TABLE_NAME = "stk_auction_o"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ StkAuctionORepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按日期范围和股票代码查询集合竞价数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）
            limit: 返回记录数

        Returns:
            集合竞价数据列表

        Examples:
            >>> repo = StkAuctionORepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range(ts_code='600000.SH')
        """
        try:
            conditions = []
            params = []

            # 如果没有指定任何日期，使用合理的默认范围
            if not start_date:
                start_date = '19900101'
            if not end_date:
                end_date = '29991231'

            conditions.append("trade_date >= %s")
            params.append(start_date)
            conditions.append("trade_date <= %s")
            params.append(end_date)

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code, trade_date, close, open, high, low,
                    vol, amount, vwap,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, vol DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "ts_code": row[0],
                    "trade_date": row[1],
                    "close": float(row[2]) if row[2] is not None else 0,
                    "open": float(row[3]) if row[3] is not None else 0,
                    "high": float(row[4]) if row[4] is not None else 0,
                    "low": float(row[5]) if row[5] is not None else 0,
                    "vol": float(row[6]) if row[6] is not None else 0,
                    "amount": float(row[7]) if row[7] is not None else 0,
                    "vwap": float(row[8]) if row[8] is not None else 0,
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询开盘集合竞价数据失败: {e}")
            raise QueryError(
                "开盘集合竞价数据查询失败",
                error_code="STK_AUCTION_O_QUERY_FAILED",
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_by_trade_date(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按交易日期查询集合竞价数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数

        Returns:
            集合竞价数据列表

        Examples:
            >>> repo = StkAuctionORepository()
            >>> data = repo.get_by_trade_date('20241122')
            >>> data = repo.get_by_trade_date('20241122', ts_code='600000.SH')
        """
        try:
            conditions = ["trade_date = %s"]
            params = [trade_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code, trade_date, close, open, high, low,
                    vol, amount, vwap,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY vol DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "ts_code": row[0],
                    "trade_date": row[1],
                    "close": float(row[2]) if row[2] is not None else 0,
                    "open": float(row[3]) if row[3] is not None else 0,
                    "high": float(row[4]) if row[4] is not None else 0,
                    "low": float(row[5]) if row[5] is not None else 0,
                    "vol": float(row[6]) if row[6] is not None else 0,
                    "amount": float(row[7]) if row[7] is not None else 0,
                    "vwap": float(row[8]) if row[8] is not None else 0,
                    "created_at": row[9].isoformat() if row[9] else None,
                    "updated_at": row[10].isoformat() if row[10] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询指定日期集合竞价数据失败: {e}")
            raise QueryError(
                "指定日期集合竞价数据查询失败",
                error_code="STK_AUCTION_O_DATE_QUERY_FAILED",
                trade_date=trade_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取集合竞价统计信息

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
                    COUNT(DISTINCT ts_code) as stock_count,
                    MAX(trade_date) as latest_date,
                    COUNT(*) as total_records,
                    AVG(vol) as avg_vol,
                    MAX(vol) as max_vol,
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
                    "avg_vol": float(row[3]) if row[3] is not None else 0,
                    "max_vol": float(row[4]) if row[4] is not None else 0,
                    "avg_amount": float(row[5]) if row[5] is not None else 0,
                    "max_amount": float(row[6]) if row[6] is not None else 0
                }

            return {
                "stock_count": 0,
                "latest_date": "",
                "total_records": 0,
                "avg_vol": 0,
                "max_vol": 0,
                "avg_amount": 0,
                "max_amount": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取集合竞价统计失败: {e}")
            raise QueryError(
                "集合竞价统计查询失败",
                error_code="STK_AUCTION_O_STATS_FAILED",
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

    def get_top_by_vol(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        按成交量排名查询集合竞价数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数

        Returns:
            成交量排名列表

        Examples:
            >>> top20 = repo.get_top_by_vol('20241122', limit=20)
        """
        try:
            query = f"""
                SELECT
                    ts_code, trade_date, close, open, high, low,
                    vol, amount, vwap
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY vol DESC
                LIMIT %s
            """

            results = self.execute_query(query, (trade_date, limit))

            return [
                {
                    "ts_code": row[0],
                    "trade_date": row[1],
                    "close": float(row[2]) if row[2] is not None else 0,
                    "open": float(row[3]) if row[3] is not None else 0,
                    "high": float(row[4]) if row[4] is not None else 0,
                    "low": float(row[5]) if row[5] is not None else 0,
                    "vol": float(row[6]) if row[6] is not None else 0,
                    "amount": float(row[7]) if row[7] is not None else 0,
                    "vwap": float(row[8]) if row[8] is not None else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询成交量排名失败: {e}")
            raise QueryError(
                "成交量排名查询失败",
                error_code="STK_AUCTION_O_TOP_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新集合竞价数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 集合竞价数据 DataFrame，必须包含 ts_code, trade_date 等列

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
            required_columns = {'ts_code', 'trade_date'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"开盘集合竞价 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换numpy数值类型为Python float
                if isinstance(value, (int, float)) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)) or (hasattr(value, 'dtype') and 'int' in str(value.dtype)):
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return None
                return value

            # 构建插入语句
            columns = ['ts_code', 'trade_date', 'close', 'open', 'high', 'low', 'vol', 'amount', 'vwap']

            # 确保所有列都存在（缺失的填充为NULL）
            for col in columns:
                if col not in df.columns:
                    df[col] = None

            # 准备插入数据（对每个字段应用类型转换）
            values = []
            for _, row in df.iterrows():
                values.append((
                    row.get('ts_code'),
                    row.get('trade_date'),
                    to_python_type(row.get('close')),
                    to_python_type(row.get('open')),
                    to_python_type(row.get('high')),
                    to_python_type(row.get('low')),
                    to_python_type(row.get('vol')),
                    to_python_type(row.get('amount')),
                    to_python_type(row.get('vwap'))
                ))

            if not values:
                return 0

            # 构建SQL - UPSERT语义
            # 主键: (ts_code, trade_date)
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            # 排除主键字段，只更新非主键列
            update_columns = ','.join([
                f"{col} = EXCLUDED.{col}"
                for col in columns if col not in ['ts_code', 'trade_date']
            ])

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (ts_code, trade_date)
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

                logger.info(f"✓ 批量插入/更新开盘集合竞价数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入开盘集合竞价数据失败: {e}")
            raise DatabaseError(
                "开盘集合竞价数据批量插入失败",
                error_code="STK_AUCTION_O_BULK_INSERT_FAILED",
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
        删除指定日期范围的集合竞价数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选，不指定则删除所有股票）

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
            logger.info(f"✓ 删除开盘集合竞价数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除开盘集合竞价数据失败: {e}")
            raise DatabaseError(
                "开盘集合竞价数据删除失败",
                error_code="STK_AUCTION_O_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            是否存在
        """
        try:
            if ts_code:
                return self.exists(
                    self.TABLE_NAME,
                    "trade_date = %s AND ts_code = %s",
                    (trade_date, ts_code)
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
