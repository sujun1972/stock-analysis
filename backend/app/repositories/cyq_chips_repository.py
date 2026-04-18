"""
每日筹码分布数据 Repository

提供 cyq_chips 表的数据访问接口
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class CyqChipsRepository(BaseRepository):
    """每日筹码分布数据 Repository"""

    TABLE_NAME = "cyq_chips"

    SORTABLE_COLUMNS = {'trade_date', 'price', 'percent', 'ts_code'}

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CyqChipsRepository initialized")

    def get_by_date_range(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> List[Dict]:
        """
        按日期范围和股票代码查询筹码分布数据（支持分页和排序）

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            page: 页码（从1开始）
            page_size: 每页记录数
            sort_by: 排序字段（白名单校验）
            sort_order: 排序方向 asc/desc

        Returns:
            筹码分布数据列表
        """
        conditions = []
        params = []

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)
        else:
            conditions.append("trade_date >= %s")
            params.append('19900101')

        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)
        else:
            conditions.append("trade_date <= %s")
            params.append('29991231')

        where_clause = " AND ".join(conditions)

        # 排序（白名单防注入）
        order = 'ASC' if sort_order == 'asc' else 'DESC'
        if sort_by and sort_by in self.SORTABLE_COLUMNS:
            order_clause = f"ORDER BY {sort_by} {order} NULLS LAST"
        else:
            order_clause = "ORDER BY trade_date DESC, ts_code, price DESC"

        offset = (page - 1) * page_size
        query = f"""
            SELECT ts_code, trade_date, price, percent,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_total_count(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """获取满足条件的记录总数（用于分页）"""
        conditions = []
        params = []

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)
        else:
            conditions.append("trade_date >= %s")
            params.append('19900101')

        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)
        else:
            conditions.append("trade_date <= %s")
            params.append('29991231')

        where_clause = " AND ".join(conditions)
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
        result = self.execute_query(query, tuple(params))
        return int(result[0][0]) if result else 0

    def get_by_code_and_date_range(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询筹码分布数据

        Args:
            ts_code: 股票代码，如 '600000.SH'
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数限制（可选）

        Returns:
            筹码分布数据列表

        Examples:
            >>> repo = CyqChipsRepository()
            >>> data = repo.get_by_code_and_date_range('600000.SH', '20240101', '20240131')
        """
        query = f"""
            SELECT ts_code, trade_date, price, percent,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
        """
        params = [ts_code]

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        query += " ORDER BY trade_date DESC, price DESC"

        query += " LIMIT %s"
        params.append(self._enforce_limit(limit))

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_trade_date(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按交易日期查询筹码分布数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数限制（可选）

        Returns:
            筹码分布数据列表

        Examples:
            >>> repo = CyqChipsRepository()
            >>> data = repo.get_by_trade_date('20240115')
        """
        query = f"""
            SELECT ts_code, trade_date, price, percent,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """
        params = [trade_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY ts_code, price DESC"

        query += " LIMIT %s"
        params.append(self._enforce_limit(limit))

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期（YYYYMMDD格式），如果没有数据则返回 None

        Examples:
            >>> repo = CyqChipsRepository()
            >>> latest_date = repo.get_latest_trade_date('600000.SH')
        """
        if ts_code:
            query = f"""
                SELECT MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
                WHERE ts_code = %s
            """
            result = self.execute_query(query, (ts_code,))
        else:
            query = f"""
                SELECT MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
            """
            result = self.execute_query(query)

        if result and result[0][0]:
            return result[0][0]
        return None

    def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取筹码分布统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = CyqChipsRepository()
            >>> stats = repo.get_statistics('600000.SH', '20240101', '20240131')
        """
        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(DISTINCT trade_date) as date_count,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params) if params else None)

        if result:
            row = result[0]
            return {
                "total_records": row[0],
                "stock_count": row[1],
                "date_count": row[2],
                "earliest_date": row[3],
                "latest_date": row[4],
                "avg_price": float(row[5]) if row[5] is not None else None,
                "min_price": float(row[6]) if row[6] is not None else None,
                "max_price": float(row[7]) if row[7] is not None else None,
            }

        return {
            "total_records": 0,
            "stock_count": 0,
            "date_count": 0,
            "earliest_date": None,
            "latest_date": None,
            "avg_price": None,
            "min_price": None,
            "max_price": None,
        }

    def get_record_count(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数量

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            记录数量

        Examples:
            >>> repo = CyqChipsRepository()
            >>> count = repo.get_record_count('600000.SH', '20240101', '20240131')
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
        params = []

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params) if params else None)
        return result[0][0] if result else 0

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入或更新筹码分布数据

        使用 PostgreSQL 的 ON CONFLICT DO UPDATE 实现 UPSERT 语义

        Args:
            df: 包含筹码分布数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = CyqChipsRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame is empty, skipping bulk_upsert")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """
            将pandas/numpy类型转换为Python原生类型

            ⚠️ 关键问题：psycopg2无法直接处理numpy类型
            必须转换为Python原生类型（int, float, None）
            """
            if pd.isna(value):
                return None
            # 转换numpy整数类型为Python int
            if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            # 转换numpy浮点类型为Python float
            if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                return float(value)
            return value

        # 准备插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('price')),
                to_python_type(row.get('percent')),
            ))

        # UPSERT 查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, trade_date, price, percent, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ts_code, trade_date, price)
            DO UPDATE SET
                percent = EXCLUDED.percent,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"成功插入/更新 {count} 条筹码分布记录")
        return count

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围内的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = CyqChipsRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131', '600000.SH')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        count = self.execute_update(query, tuple(params))
        logger.info(f"删除了 {count} 条筹码分布记录")
        return count

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            True 如果数据存在，否则 False

        Examples:
            >>> repo = CyqChipsRepository()
            >>> exists = repo.exists_by_date('20240115', '600000.SH')
        """
        query = f"SELECT 1 FROM {self.TABLE_NAME} WHERE trade_date = %s"
        params = [trade_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " LIMIT 1"

        result = self.execute_query(query, tuple(params))
        return len(result) > 0

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行（tuple）

        Returns:
            数据字典
        """
        return {
            "ts_code": row[0],
            "trade_date": row[1],
            "price": float(row[2]) if row[2] is not None else None,
            "percent": float(row[3]) if row[3] is not None else None,
            "created_at": row[4].isoformat() if row[4] else None,
            "updated_at": row[5].isoformat() if row[5] else None,
        }
