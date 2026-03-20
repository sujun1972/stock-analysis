"""
融资融券交易明细数据访问层

提供融资融券交易明细数据的增删改查操作，支持按日期范围、股票代码查询，
以及批量插入、统计分析等功能。

数据表: margin_detail
数据源: Tushare 沪深两市每日融资融券明细
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class MarginDetailRepository(BaseRepository):
    """
    融资融券交易明细数据访问层

    职责：
    - 按日期范围和股票代码查询融资融券明细数据
    - 批量插入/更新融资融券明细数据
    - 获取融资融券明细统计信息
    - 查询融资融券余额排名
    """

    TABLE_NAME = "margin_detail"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ MarginDetailRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询融资融券明细数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            融资融券明细数据列表

        Examples:
            >>> repo = MarginDetailRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    rzye,
                    rqye,
                    rzmre,
                    rqyl,
                    rzche,
                    rqchl,
                    rqmcl,
                    rzrqye,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, rzrqye DESC
            """

            if limit:
                query += f" LIMIT {int(limit)}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, tuple(params))

            return [
                {
                    "trade_date": row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else row[0],
                    "ts_code": row[1],
                    "name": row[2],
                    "rzye": float(row[3]) if row[3] else 0,
                    "rqye": float(row[4]) if row[4] else 0,
                    "rzmre": float(row[5]) if row[5] else 0,
                    "rqyl": float(row[6]) if row[6] else 0,
                    "rzche": float(row[7]) if row[7] else 0,
                    "rqchl": float(row[8]) if row[8] else 0,
                    "rqmcl": float(row[9]) if row[9] else 0,
                    "rzrqye": float(row[10]) if row[10] else 0,
                    "created_at": row[11].isoformat() if row[11] else None,
                    "updated_at": row[12].isoformat() if row[12] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询融资融券明细数据失败: {e}")
            raise QueryError(
                "融资融券明细数据查询失败",
                error_code="MARGIN_DETAIL_QUERY_FAILED",
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取融资融券明细统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计数据字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"平均融资融券余额: {stats['avg_rzrqye']}")
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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    AVG(rzrqye) as avg_rzrqye,
                    SUM(rzrqye) as total_rzrqye,
                    MAX(rzrqye) as max_rzrqye,
                    AVG(rzye) as avg_rzye,
                    AVG(rqye) as avg_rqye,
                    SUM(rzmre) as total_rzmre,
                    SUM(rzche) as total_rzche,
                    MAX(trade_date) as latest_date,
                    MIN(trade_date) as earliest_date,
                    COUNT(*) as count,
                    COUNT(DISTINCT ts_code) as stock_count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and result[0]:
                row = result[0]
                return {
                    "avg_rzrqye": float(row[0]) if row[0] else 0,
                    "total_rzrqye": float(row[1]) if row[1] else 0,
                    "max_rzrqye": float(row[2]) if row[2] else 0,
                    "avg_rzye": float(row[3]) if row[3] else 0,
                    "avg_rqye": float(row[4]) if row[4] else 0,
                    "total_rzmre": float(row[5]) if row[5] else 0,
                    "total_rzche": float(row[6]) if row[6] else 0,
                    "latest_date": row[7] or "",
                    "earliest_date": row[8] or "",
                    "count": row[9] or 0,
                    "stock_count": row[10] or 0
                }

            return {
                "avg_rzrqye": 0, "total_rzrqye": 0, "max_rzrqye": 0,
                "avg_rzye": 0, "avg_rqye": 0,
                "total_rzmre": 0, "total_rzche": 0,
                "latest_date": "", "earliest_date": "",
                "count": 0, "stock_count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取融资融券明细统计失败: {e}")
            raise QueryError(
                "融资融券明细统计查询失败",
                error_code="MARGIN_DETAIL_STATS_FAILED",
                reason=str(e)
            )

    def get_top_by_rzrqye(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期融资融券余额排名前N的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数

        Returns:
            排名前N的股票列表

        Examples:
            >>> top_stocks = repo.get_top_by_rzrqye('20240115', limit=10)
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    rzrqye,
                    rzye,
                    rqye,
                    rzmre,
                    rzche
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY rzrqye DESC
                LIMIT %s
            """

            results = self.execute_query(query, (trade_date, limit))

            return [
                {
                    "trade_date": row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else row[0],
                    "ts_code": row[1],
                    "name": row[2],
                    "rzrqye": float(row[3]) if row[3] else 0,
                    "rzye": float(row[4]) if row[4] else 0,
                    "rqye": float(row[5]) if row[5] else 0,
                    "rzmre": float(row[6]) if row[6] else 0,
                    "rzche": float(row[7]) if row[7] else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"获取融资融券余额排名失败: {e}")
            raise QueryError(
                "融资融券余额排名查询失败",
                error_code="MARGIN_DETAIL_TOP_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期（格式：YYYYMMDD），如果没有数据则返回None
        """
        try:
            if ts_code:
                query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME} WHERE ts_code = %s"
                result = self.execute_query(query, (ts_code,))
            else:
                query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
                result = self.execute_query(query)

            if result and result[0][0]:
                date_value = result[0][0]
                # 将 datetime.date 转换为字符串 YYYYMMDD
                return date_value.strftime('%Y%m%d') if hasattr(date_value, 'strftime') else date_value
            return None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def get_by_trade_date(self, trade_date: str) -> List[Dict]:
        """
        获取指定日期所有股票的融资融券明细数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            该日期所有股票的数据列表
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    rzye,
                    rqye,
                    rzmre,
                    rqyl,
                    rzche,
                    rqchl,
                    rqmcl,
                    rzrqye
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY rzrqye DESC
            """

            results = self.execute_query(query, (trade_date,))

            return [
                {
                    "trade_date": row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else row[0],
                    "ts_code": row[1],
                    "name": row[2],
                    "rzye": float(row[3]) if row[3] else 0,
                    "rqye": float(row[4]) if row[4] else 0,
                    "rzmre": float(row[5]) if row[5] else 0,
                    "rqyl": float(row[6]) if row[6] else 0,
                    "rzche": float(row[7]) if row[7] else 0,
                    "rqchl": float(row[8]) if row[8] else 0,
                    "rqmcl": float(row[9]) if row[9] else 0,
                    "rzrqye": float(row[10]) if row[10] else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询指定日期融资融券明细数据失败: {e}")
            raise QueryError(
                "融资融券明细数据查询失败",
                error_code="MARGIN_DETAIL_QUERY_BY_DATE_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新融资融券明细数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 融资融券明细数据 DataFrame，必须包含 trade_date, ts_code 等列

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
            required_columns = {'trade_date', 'ts_code'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"融资融券明细 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = [
                'trade_date', 'ts_code', 'name',
                'rzye', 'rqye', 'rzmre', 'rqyl',
                'rzche', 'rqchl', 'rqmcl', 'rzrqye'
            ]

            # 确保所有列都存在（缺失的填充为默认值）
            for col in columns:
                if col not in df.columns:
                    if col == 'name':
                        df[col] = None
                    elif col not in ['trade_date', 'ts_code']:
                        df[col] = 0

            # 准备数据
            values = []
            for _, row in df.iterrows():
                values.append(tuple(row[col] for col in columns))

            if not values:
                return 0

            # 构建SQL
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            update_columns = ','.join([
                f"{col} = EXCLUDED.{col}"
                for col in columns if col not in ['trade_date', 'ts_code']
            ])

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (trade_date, ts_code)
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

                logger.info(f"✓ 批量插入/更新融资融券明细数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入融资融券明细数据失败: {e}")
            raise DatabaseError(
                "融资融券明细数据批量插入失败",
                error_code="MARGIN_DETAIL_BULK_INSERT_FAILED",
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
        删除指定日期范围的融资融券明细数据

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
            logger.info(f"✓ 删除融资融券明细数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除融资融券明细数据失败: {e}")
            raise DatabaseError(
                "融资融券明细数据删除失败",
                error_code="MARGIN_DETAIL_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(
        self,
        trade_date: str,
        ts_code: Optional[str] = None
    ) -> bool:
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
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else None

            return self.count(
                self.TABLE_NAME,
                where_clause,
                tuple(params) if params else None
            )
        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0

    def get_stock_list(self, trade_date: Optional[str] = None) -> List[str]:
        """
        获取有融资融券数据的股票代码列表

        Args:
            trade_date: 交易日期（可选，不指定则返回所有股票）

        Returns:
            股票代码列表
        """
        try:
            if trade_date:
                query = f"""
                    SELECT DISTINCT ts_code
                    FROM {self.TABLE_NAME}
                    WHERE trade_date = %s
                    ORDER BY ts_code
                """
                results = self.execute_query(query, (trade_date,))
            else:
                query = f"""
                    SELECT DISTINCT ts_code
                    FROM {self.TABLE_NAME}
                    ORDER BY ts_code
                """
                results = self.execute_query(query)

            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
