"""
股东人数数据 Repository

管理 stk_holdernumber 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class StkHolderNumberRepository(BaseRepository):
    """股东人数数据仓储"""

    TABLE_NAME = "stk_holdernumber"

    def __init__(self, db=None):
        super().__init__(db)

    def get_by_code_and_date_range(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询股东人数数据

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数限制

        Returns:
            股东人数数据列表

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> data = repo.get_by_code_and_date_range('000001.SZ', '20240101', '20241231')
        """
        query = f"""
            SELECT
                ts_code, ann_date, end_date, holder_num,
                created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)

        query += " ORDER BY ann_date DESC, ts_code"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params) if params else None)

        return [
            {
                "ts_code": row[0],
                "ann_date": row[1],
                "end_date": row[2],
                "holder_num": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
            for row in result
        ]

    def get_latest_by_code(self, ts_code: str, limit: int = 10) -> List[Dict]:
        """
        获取指定股票的最新股东人数数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            最新的股东人数数据列表

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> data = repo.get_latest_by_code('000001.SZ', 10)
        """
        query = f"""
            SELECT
                ts_code, ann_date, end_date, holder_num,
                created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
            ORDER BY ann_date DESC
            LIMIT %s
        """

        result = self.execute_query(query, (ts_code, limit))

        return [
            {
                "ts_code": row[0],
                "ann_date": row[1],
                "end_date": row[2],
                "holder_num": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
            for row in result
        ]

    def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取股东人数统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> stats = repo.get_statistics('000001.SZ', '20240101', '20241231')
        """
        query = f"""
            SELECT
                COUNT(*) as record_count,
                AVG(holder_num) as avg_holder_num,
                MAX(holder_num) as max_holder_num,
                MIN(holder_num) as min_holder_num,
                COUNT(DISTINCT ts_code) as stock_count
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params) if params else None)

        if result and result[0]:
            row = result[0]
            return {
                "record_count": row[0] or 0,
                "avg_holder_num": float(row[1]) if row[1] else 0,
                "max_holder_num": row[2] or 0,
                "min_holder_num": row[3] or 0,
                "stock_count": row[4] or 0
            }

        return {
            "record_count": 0,
            "avg_holder_num": 0,
            "max_holder_num": 0,
            "min_holder_num": 0,
            "stock_count": 0
        }

    def get_latest_ann_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新公告日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新公告日期（YYYYMMDD），如果没有数据则返回None

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> latest_date = repo.get_latest_ann_date('000001.SZ')
        """
        query = f"""
            SELECT MAX(ann_date)
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params) if params else None)

        if result and result[0] and result[0][0]:
            return result[0][0]

        return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新股东人数数据

        Args:
            df: 包含股东人数数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """
            将pandas/numpy类型转换为Python原生类型

            关键问题：psycopg2无法直接处理numpy类型
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
                to_python_type(row.get('ann_date')),
                to_python_type(row.get('end_date')),
                to_python_type(row.get('holder_num'))
            ))

        # 批量插入/更新
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, ann_date, end_date, holder_num, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ts_code, ann_date, end_date)
            DO UPDATE SET
                holder_num = EXCLUDED.holder_num,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"批量插入/更新 {count} 条股东人数数据")

        return count

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> count = repo.delete_by_date_range('20240101', '20241231', '000001.SZ')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE ann_date >= %s AND ann_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        count = self.execute_update(query, tuple(params))
        logger.info(f"删除 {count} 条股东人数数据")

        return count

    def exists_by_date(self, ann_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            存在返回True，否则返回False

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> exists = repo.exists_by_date('20240101', '000001.SZ')
        """
        query = f"""
            SELECT COUNT(*)
            FROM {self.TABLE_NAME}
            WHERE ann_date = %s
        """
        params = [ann_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params))

        return result[0][0] > 0 if result else False

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

        Examples:
            >>> repo = StkHolderNumberRepository()
            >>> count = repo.get_record_count('20240101', '20241231', '000001.SZ')
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
        params = []

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params) if params else None)

        return result[0][0] if result else 0
