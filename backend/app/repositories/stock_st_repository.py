"""
ST股票列表 Repository

管理 stock_st 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class StockStRepository(BaseRepository):
    """ST股票列表 Repository"""

    TABLE_NAME = "stock_st"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StockStRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        st_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询ST股票数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            st_type: ST类型（可选）
            limit: 限制返回数量

        Returns:
            ST股票数据列表

        Examples:
            >>> repo = StockStRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if st_type:
                conditions.append("type = %s")
                params.append(st_type)

            where_clause = " AND ".join(conditions)
            limit_clause = f"LIMIT {limit}" if limit else ""

            query = f"""
                SELECT ts_code, trade_date, name, type, type_name,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
                {limit_clause}
            """

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询ST股票数据失败: {e}")
            raise

    def get_by_trade_date(self, trade_date: str) -> List[Dict]:
        """
        获取指定交易日的所有ST股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            ST股票列表

        Examples:
            >>> repo = StockStRepository()
            >>> data = repo.get_by_trade_date('20240115')
        """
        try:
            query = f"""
                SELECT ts_code, trade_date, name, type, type_name,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY ts_code
            """
            result = self.execute_query(query, (trade_date,))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询指定日期ST股票失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取ST股票统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StockStRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
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
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as unique_stocks,
                    COUNT(DISTINCT trade_date) as trading_days,
                    COUNT(DISTINCT type) as st_types,
                    MAX(trade_date) as latest_date,
                    MIN(trade_date) as earliest_date
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    "total_records": row[0] or 0,
                    "unique_stocks": row[1] or 0,
                    "trading_days": row[2] or 0,
                    "st_types": row[3] or 0,
                    "latest_date": row[4],
                    "earliest_date": row[5]
                }

            return {
                "total_records": 0,
                "unique_stocks": 0,
                "trading_days": 0,
                "st_types": 0,
                "latest_date": None,
                "earliest_date": None
            }

        except Exception as e:
            logger.error(f"获取ST股票统计信息失败: {e}")
            raise

    def get_type_distribution(self, trade_date: Optional[str] = None) -> List[Dict]:
        """
        获取ST类型分布统计

        Args:
            trade_date: 交易日期（可选），如不指定则统计所有数据

        Returns:
            类型分布列表

        Examples:
            >>> repo = StockStRepository()
            >>> dist = repo.get_type_distribution('20240115')
        """
        try:
            where_clause = "WHERE trade_date = %s" if trade_date else ""
            params = (trade_date,) if trade_date else ()

            query = f"""
                SELECT type, type_name, COUNT(*) as count
                FROM {self.TABLE_NAME}
                {where_clause}
                GROUP BY type, type_name
                ORDER BY count DESC
            """

            result = self.execute_query(query, params)
            return [
                {
                    "type": row[0],
                    "type_name": row[1],
                    "count": row[2]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"获取ST类型分布失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期字符串 YYYYMMDD，如无数据则返回 None

        Examples:
            >>> repo = StockStRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        try:
            query = f"""
                SELECT MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
            """
            result = self.execute_query(query)
            return result[0][0] if result and result[0][0] else None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入或更新ST股票数据

        Args:
            df: 包含ST股票数据的DataFrame

        Returns:
            影响的行数

        Examples:
            >>> repo = StockStRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                if pd.isna(value):
                    return None
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('type')),
                    to_python_type(row.get('type_name'))
                ))

            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, trade_date, name, type, type_name)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ts_code, trade_date)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    type_name = EXCLUDED.type_name,
                    updated_at = CURRENT_TIMESTAMP
            """

            count = self.execute_batch(query, values)
            logger.info(f"批量插入/更新ST股票数据成功: {count} 条")
            return count

        except Exception as e:
            logger.error(f"批量插入ST股票数据失败: {e}")
            raise

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的行数

        Examples:
            >>> repo = StockStRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除日期范围 {start_date} ~ {end_date} 的数据: {count} 条")
            return count

        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            raise

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = StockStRepository()
            >>> exists = repo.exists_by_date('20240115')
        """
        try:
            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE trade_date = %s
            """
            result = self.execute_query(query, (trade_date,))
            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            raise

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数量

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            记录数量

        Examples:
            >>> repo = StockStRepository()
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

            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数量失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 数据库查询结果行

        Returns:
            字典格式的数据
        """
        return {
            "ts_code": row[0],
            "trade_date": row[1],
            "name": row[2],
            "type": row[3],
            "type_name": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
            "updated_at": row[6].isoformat() if row[6] else None
        }
