"""
融资融券标的 Repository

管理 margin_secs 表的数据访问
Tushare 接口: margin_secs - 融资融券标的（盘前更新）
"""

from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class MarginSecsRepository(BaseRepository):
    """融资融券标的数据访问层"""

    TABLE_NAME = "margin_secs"

    def __init__(self, db=None):
        """初始化 Repository"""
        super().__init__(db)
        logger.debug("✓ MarginSecsRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        按日期范围查询融资融券标的

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 标的代码（可选）
            exchange: 交易所代码（可选，SSE/SZSE/BSE）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = MarginSecsRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240417', exchange='SSE')
        """
        try:
            conditions = ["trade_date >= %s"]
            params = [start_date]

            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if exchange:
                conditions.append("exchange = %s")
                params.append(exchange)

            where_clause = " AND ".join(conditions)
            query = f"""
                SELECT
                    trade_date, ts_code, name, exchange,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
                LIMIT %s
            """
            params.append(limit)

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询融资融券标的失败: {e}")
            raise QueryError(
                "查询融资融券标的失败",
                error_code="MARGIN_SECS_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_trade_date(self, trade_date: str, exchange: Optional[str] = None) -> List[Dict]:
        """
        按交易日期查询融资融券标的

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            exchange: 交易所代码（可选，SSE/SZSE/BSE）

        Returns:
            数据列表

        Examples:
            >>> repo = MarginSecsRepository()
            >>> data = repo.get_by_trade_date('20240417')
            >>> data = repo.get_by_trade_date('20240417', exchange='SSE')
        """
        try:
            if exchange:
                query = f"""
                    SELECT
                        trade_date, ts_code, name, exchange,
                        created_at, updated_at
                    FROM {self.TABLE_NAME}
                    WHERE trade_date = %s AND exchange = %s
                    ORDER BY ts_code
                """
                result = self.execute_query(query, (trade_date, exchange))
            else:
                query = f"""
                    SELECT
                        trade_date, ts_code, name, exchange,
                        created_at, updated_at
                    FROM {self.TABLE_NAME}
                    WHERE trade_date = %s
                    ORDER BY exchange, ts_code
                """
                result = self.execute_query(query, (trade_date,))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"按交易日期查询失败: {e}")
            raise QueryError(
                "按交易日期查询融资融券标的失败",
                error_code="MARGIN_SECS_DATE_QUERY_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），无数据时返回 None

        Examples:
            >>> repo = MarginSecsRepository()
            >>> latest_date = repo.get_latest_trade_date()
            >>> print(latest_date)  # '20240417'
        """
        try:
            query = f"""
                SELECT MAX(trade_date) as max_date
                FROM {self.TABLE_NAME}
            """
            result = self.execute_query(query)
            if result and result[0][0]:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise QueryError(
                "获取最新交易日期失败",
                error_code="MARGIN_SECS_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            exchange: 交易所代码（可选）

        Returns:
            统计数据字典

        Examples:
            >>> repo = MarginSecsRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(stats['total_count'])
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

            if exchange:
                conditions.append("exchange = %s")
                params.append(exchange)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as unique_stocks,
                    COUNT(DISTINCT trade_date) as trading_days,
                    COUNT(DISTINCT exchange) as exchange_count
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            if result:
                row = result[0]
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'unique_stocks': int(row[1]) if row[1] else 0,
                    'trading_days': int(row[2]) if row[2] else 0,
                    'exchange_count': int(row[3]) if row[3] else 0
                }
            return {'total_count': 0, 'unique_stocks': 0, 'trading_days': 0, 'exchange_count': 0}

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "获取统计信息失败",
                error_code="MARGIN_SECS_STATS_FAILED",
                reason=str(e)
            )

    def get_exchange_distribution(self, trade_date: str) -> List[Dict]:
        """
        获取指定日期的交易所分布统计

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            交易所分布列表

        Examples:
            >>> repo = MarginSecsRepository()
            >>> dist = repo.get_exchange_distribution('20240417')
            >>> print(dist)  # [{'exchange': 'SSE', 'count': 1786}, ...]
        """
        try:
            query = f"""
                SELECT
                    exchange,
                    COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                GROUP BY exchange
                ORDER BY count DESC
            """
            result = self.execute_query(query, (trade_date,))
            return [
                {'exchange': row[0], 'count': int(row[1])}
                for row in result
            ]

        except Exception as e:
            logger.error(f"获取交易所分布失败: {e}")
            raise QueryError(
                "获取交易所分布失败",
                error_code="MARGIN_SECS_EXCHANGE_DIST_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df) -> int:
        """
        批量插入/更新数据（UPSERT）

        Args:
            df: pandas DataFrame，包含 trade_date, ts_code, name, exchange 列

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = MarginSecsRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'trade_date': ['20240417', '20240417'],
            ...     'ts_code': ['510050.SH', '510100.SH'],
            ...     'name': ['50ETF', 'SZ50ETF'],
            ...     'exchange': ['SSE', 'SSE']
            ... })
            >>> count = repo.bulk_upsert(df)
        """
        try:
            if df.empty:
                logger.warning("DataFrame 为空，跳过插入")
                return 0

            # 确保必需列存在
            required_columns = ['trade_date', 'ts_code', 'name', 'exchange']
            missing_columns = set(required_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"缺少必需列: {missing_columns}")

            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, ts_code, name, exchange)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    exchange = EXCLUDED.exchange,
                    updated_at = CURRENT_TIMESTAMP
            """

            values = [
                (
                    row['trade_date'],
                    row['ts_code'],
                    row['name'],
                    row['exchange']
                )
                for _, row in df.iterrows()
            ]

            affected_rows = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {affected_rows} 条融资融券标的记录")
            return affected_rows

        except Exception as e:
            logger.error(f"批量插入融资融券标的失败: {e}")
            raise QueryError(
                "批量插入融资融券标的失败",
                error_code="MARGIN_SECS_BULK_INSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(self, start_date: str, end_date: Optional[str] = None) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = MarginSecsRepository()
            >>> deleted = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            if end_date:
                query = f"""
                    DELETE FROM {self.TABLE_NAME}
                    WHERE trade_date >= %s AND trade_date <= %s
                """
                params = (start_date, end_date)
            else:
                query = f"""
                    DELETE FROM {self.TABLE_NAME}
                    WHERE trade_date = %s
                """
                params = (start_date,)

            affected_rows = self.execute_update(query, params)
            logger.info(f"成功删除 {affected_rows} 条记录")
            return affected_rows

        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            raise QueryError(
                "删除融资融券标的数据失败",
                error_code="MARGIN_SECS_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = MarginSecsRepository()
            >>> exists = repo.exists_by_date('20240417')
        """
        try:
            query = f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.TABLE_NAME}
                    WHERE trade_date = %s
                )
            """
            result = self.execute_query(query, (trade_date,))
            return result[0][0] if result else False

        except Exception as e:
            logger.error(f"检查数据存在性失败: {e}")
            raise QueryError(
                "检查数据存在性失败",
                error_code="MARGIN_SECS_EXISTS_CHECK_FAILED",
                reason=str(e)
            )

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            记录数

        Examples:
            >>> repo = MarginSecsRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
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

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            return int(result[0][0]) if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            raise QueryError(
                "获取记录数失败",
                error_code="MARGIN_SECS_COUNT_FAILED",
                reason=str(e)
            )

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'name': row[2],
            'exchange': row[3],
            'created_at': row[4],
            'updated_at': row[5]
        }
