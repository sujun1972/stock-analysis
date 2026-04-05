"""
财务审计意见数据 Repository

Author: Claude
Date: 2026-03-22
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class FinaAuditRepository(BaseRepository):
    """财务审计意见数据 Repository"""

    TABLE_NAME = "fina_audit"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ FinaAuditRepository initialized")

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        conditions = []
        params = []
        if start_date:
            conditions.append("ann_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("ann_date <= %s")
            params.append(end_date)
        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
        result = self.execute_query(query, tuple(params) if params else None)
        return int(result[0][0]) if result else 0

    def get_by_ts_code(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码查询财务审计意见数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期（公告日期），格式：YYYYMMDD
            end_date: 结束日期（公告日期），格式：YYYYMMDD
            limit: 限制返回记录数

        Returns:
            财务审计意见数据列表

        Examples:
            >>> repo = FinaAuditRepository()
            >>> data = repo.get_by_ts_code('600000.SH', '20200101', '20201231')
        """
        conditions = ["ts_code = %s"]
        params = [ts_code]

        if start_date:
            conditions.append("ann_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("ann_date <= %s")
            params.append(end_date)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT ts_code, ann_date, end_date, audit_result, audit_fees,
                   audit_agency, audit_sign, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY ann_date DESC, end_date DESC
        """

        if limit:
            query += f" LIMIT {int(limit)}"

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询财务审计意见数据

        Args:
            start_date: 开始日期（公告日期），格式：YYYYMMDD
            end_date: 结束日期（公告日期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 限制返回记录数

        Returns:
            财务审计意见数据列表

        Examples:
            >>> repo = FinaAuditRepository()
            >>> data = repo.get_by_date_range('20200101', '20201231')
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("ann_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("ann_date <= %s")
            params.append(end_date)

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT ts_code, ann_date, end_date, audit_result, audit_fees,
                   audit_agency, audit_sign, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY ann_date DESC, end_date DESC
        """

        if limit:
            query += f" LIMIT {int(limit)}"

        if offset:
            query += f" OFFSET {int(offset)}"

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_latest_by_ts_code(self, ts_code: str) -> Optional[Dict]:
        """
        获取指定股票的最新审计意见

        Args:
            ts_code: 股票代码

        Returns:
            最新的审计意见数据，如果不存在则返回 None

        Examples:
            >>> repo = FinaAuditRepository()
            >>> latest = repo.get_latest_by_ts_code('600000.SH')
        """
        query = f"""
            SELECT ts_code, ann_date, end_date, audit_result, audit_fees,
                   audit_agency, audit_sign, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
            ORDER BY ann_date DESC, end_date DESC
            LIMIT 1
        """
        result = self.execute_query(query, (ts_code,))
        if result:
            return self._row_to_dict(result[0])
        return None

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取审计意见统计信息

        Args:
            start_date: 开始日期（公告日期），格式：YYYYMMDD
            end_date: 结束日期（公告日期），格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = FinaAuditRepository()
            >>> stats = repo.get_statistics('20200101', '20201231')
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("ann_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("ann_date <= %s")
            params.append(end_date)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(DISTINCT audit_agency) as agency_count,
                AVG(audit_fees) as avg_fees,
                MAX(audit_fees) as max_fees,
                MIN(audit_fees) as min_fees
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
        """

        result = self.execute_query(query, tuple(params))
        if result:
            row = result[0]
            return {
                'total_count': row[0] or 0,
                'stock_count': row[1] or 0,
                'agency_count': row[2] or 0,
                'avg_fees': float(row[3]) if row[3] else 0.0,
                'max_fees': float(row[4]) if row[4] else 0.0,
                'min_fees': float(row[5]) if row[5] else 0.0
            }
        return {
            'total_count': 0,
            'stock_count': 0,
            'agency_count': 0,
            'avg_fees': 0.0,
            'max_fees': 0.0,
            'min_fees': 0.0
        }

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新财务审计意见数据

        Args:
            df: 包含审计意见数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = FinaAuditRepository()
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

            ⚠️ 关键问题：psycopg2无法直接处理numpy类型（numpy.int64, numpy.float64等）
            必须转换为Python原生类型（int, float, None）
            否则会报错：can't adapt type 'numpy.int64' 或 integer out of range
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
                to_python_type(row.get('audit_result')),
                to_python_type(row.get('audit_fees')),
                to_python_type(row.get('audit_agency')),
                to_python_type(row.get('audit_sign'))
            ))

        # UPSERT 查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, ann_date, end_date, audit_result, audit_fees, audit_agency, audit_sign)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts_code, ann_date, end_date)
            DO UPDATE SET
                audit_result = EXCLUDED.audit_result,
                audit_fees = EXCLUDED.audit_fees,
                audit_agency = EXCLUDED.audit_agency,
                audit_sign = EXCLUDED.audit_sign,
                updated_at = CURRENT_TIMESTAMP
        """

        count = self.execute_batch(query, values)
        logger.info(f"✓ Bulk upserted {count} records to {self.TABLE_NAME}")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'end_date': row[2],
            'audit_result': row[3],
            'audit_fees': float(row[4]) if row[4] else None,
            'audit_agency': row[5],
            'audit_sign': row[6],
            'created_at': row[7].isoformat() if row[7] else None,
            'updated_at': row[8].isoformat() if row[8] else None
        }
