"""
每日涨跌停价格 Repository

管理 stk_limit_d 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class StkLimitDRepository(BaseRepository):
    """每日涨跌停价格 Repository"""

    TABLE_NAME = "stk_limit_d"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkLimitDRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询每日涨跌停价格数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = StkLimitDRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        query = f"""
            SELECT trade_date, ts_code, pre_close, up_limit, down_limit
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

        result = self.execute_query(query, tuple(params))

        return [
            {
                "trade_date": row[0],
                "ts_code": row[1],
                "pre_close": float(row[2]) if row[2] is not None else None,
                "up_limit": float(row[3]) if row[3] is not None else None,
                "down_limit": float(row[4]) if row[4] is not None else None,
            }
            for row in result
        ]

    def get_by_trade_date(self, trade_date: str, ts_code: Optional[str] = None) -> List[Dict]:
        """
        按交易日期查询数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            数据列表
        """
        return self.get_by_date_range(trade_date, trade_date, ts_code)

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典
        """
        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT trade_date) as trading_days,
                COUNT(DISTINCT ts_code) as stock_count,
                AVG(up_limit - pre_close) as avg_up_range,
                AVG(pre_close - down_limit) as avg_down_range
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params))

        if result:
            row = result[0]
            return {
                "total_records": int(row[0]) if row[0] else 0,
                "trading_days": int(row[1]) if row[1] else 0,
                "stock_count": int(row[2]) if row[2] else 0,
                "avg_up_range": float(row[3]) if row[3] is not None else 0.0,
                "avg_down_range": float(row[4]) if row[4] is not None else 0.0,
            }

        return {
            "total_records": 0,
            "trading_days": 0,
            "stock_count": 0,
            "avg_up_range": 0.0,
            "avg_down_range": 0.0,
        }

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期 (YYYYMMDD) 或 None
        """
        query = f"""
            SELECT MAX(trade_date)
            FROM {self.TABLE_NAME}
        """
        result = self.execute_query(query)

        if result and result[0][0]:
            return result[0][0]

        return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新数据（UPSERT）

        Args:
            df: 包含数据的 DataFrame

        Returns:
            插入/更新的记录数
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """
            将pandas/numpy类型转换为Python原生类型
            """
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
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('pre_close')),
                to_python_type(row.get('up_limit')),
                to_python_type(row.get('down_limit')),
            ))

        # UPSERT SQL
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (trade_date, ts_code, pre_close, up_limit, down_limit)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, ts_code)
            DO UPDATE SET
                pre_close = EXCLUDED.pre_close,
                up_limit = EXCLUDED.up_limit,
                down_limit = EXCLUDED.down_limit,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"成功插入/更新 {count} 条每日涨跌停价格记录")
        return count

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        count = self.execute_update(query, (start_date, end_date))
        logger.info(f"删除了 {count} 条每日涨跌停价格记录")
        return count

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            数据是否存在
        """
        query = f"""
            SELECT COUNT(*)
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """
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
        """
        query = f"""
            SELECT COUNT(*)
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        result = self.execute_query(query, (start_date, end_date))

        return int(result[0][0]) if result else 0
