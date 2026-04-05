"""
个股异常波动数据 Repository

负责 stk_shock 表的数据访问操作
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class StkShockRepository(BaseRepository):
    """个股异常波动数据 Repository"""

    TABLE_NAME = "stk_shock"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkShockRepository initialized")

    def get_count(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取符合条件的记录总数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            记录总数
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date >= %s AND trade_date <= %s"
        params = [start_date, end_date]
        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)
        result = self.execute_query(query, tuple(params))
        return result[0][0] if result else 0

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询个股异常波动数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = StkShockRepository()
            >>> data = repo.get_by_date_range('20260301', '20260331')
        """
        query = f"""
            SELECT ts_code, trade_date, name, trade_market, reason, period,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY trade_date DESC, ts_code"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        if offset:
            query += " OFFSET %s"
            params.append(offset)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取异常波动统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkShockRepository()
            >>> stats = repo.get_statistics('20260301', '20260331')
        """
        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ts_code) as unique_stocks,
                COUNT(DISTINCT trade_date) as unique_dates,
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date
            FROM {self.TABLE_NAME}
        """
        params = []

        if start_date and end_date:
            query += " WHERE trade_date >= %s AND trade_date <= %s"
            params = [start_date, end_date]

        result = self.execute_query(query, tuple(params) if params else None)
        if result:
            row = result[0]
            return {
                'total_records': row[0] or 0,
                'unique_stocks': row[1] or 0,
                'unique_dates': row[2] or 0,
                'earliest_date': row[3],
                'latest_date': row[4]
            }
        return {
            'total_records': 0,
            'unique_stocks': 0,
            'unique_dates': 0,
            'earliest_date': None,
            'latest_date': None
        }

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），如果表为空则返回None

        Examples:
            >>> repo = StkShockRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
        result = self.execute_query(query)
        if result and result[0][0]:
            return result[0][0]
        return None

    def get_by_trade_date(self, trade_date: str, limit: Optional[int] = None) -> List[Dict]:
        """
        获取指定日期的异常波动数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = StkShockRepository()
            >>> data = repo.get_by_trade_date('20260312')
        """
        query = f"""
            SELECT ts_code, trade_date, name, trade_market, reason, period,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
            ORDER BY ts_code
        """
        params = [trade_date]

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_stock_code(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        获取指定股票的异常波动记录

        Args:
            ts_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = StkShockRepository()
            >>> data = repo.get_by_stock_code('002015.SZ', '20250101', '20251231')
        """
        query = f"""
            SELECT ts_code, trade_date, name, trade_market, reason, period,
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

        query += " ORDER BY trade_date DESC"

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新个股异常波动数据

        Args:
            df: 包含数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkShockRepository()
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """将pandas/numpy类型转换为Python原生类型"""
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

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, trade_date, name, trade_market, reason, period, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ts_code, trade_date)
            DO UPDATE SET
                name = EXCLUDED.name,
                trade_market = EXCLUDED.trade_market,
                reason = EXCLUDED.reason,
                period = EXCLUDED.period,
                updated_at = NOW()
        """

        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('name')),
                to_python_type(row.get('trade_market')),
                to_python_type(row.get('reason')),
                to_python_type(row.get('period'))
            ))

        count = self.execute_batch(query, values)
        logger.info(f"批量插入/更新 {count} 条记录")
        return count

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = StkShockRepository()
            >>> count = repo.delete_by_date_range('20260301', '20260331')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        count = self.execute_update(query, (start_date, end_date))
        logger.info(f"删除 {count} 条记录")
        return count

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期是否有数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = StkShockRepository()
            >>> exists = repo.exists_by_date('20260312')
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date = %s"
        result = self.execute_query(query, (trade_date,))
        return result[0][0] > 0 if result else False

    def get_record_count(self, start_date: str, end_date: str) -> int:
        """
        获取指定日期范围的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = StkShockRepository()
            >>> count = repo.get_record_count('20260301', '20260331')
        """
        query = f"""
            SELECT COUNT(*)
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        result = self.execute_query(query, (start_date, end_date))
        return result[0][0] if result else 0

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行（tuple）

        Returns:
            字典格式的数据
        """
        return {
            'ts_code': row[0],
            'trade_date': row[1],
            'name': row[2],
            'trade_market': row[3],
            'reason': row[4],
            'period': row[5],
            'created_at': row[6].isoformat() if row[6] else None,
            'updated_at': row[7].isoformat() if row[7] else None
        }
