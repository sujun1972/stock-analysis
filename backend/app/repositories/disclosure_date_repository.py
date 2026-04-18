"""
财报披露计划Repository

负责disclosure_date表的数据访问操作
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class DisclosureDateRepository(BaseRepository):
    """财报披露计划Repository"""

    TABLE_NAME = "disclosure_date"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ DisclosureDateRepository initialized")

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """获取记录总数"""
        conditions = []
        params = []
        if start_date:
            conditions.append("end_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("end_date <= %s")
            params.append(end_date)
        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
        result = self.execute_query(query, tuple(params) if params else None)
        return int(result[0][0]) if result else 0

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询财报披露计划数据

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 限制返回记录数

        Returns:
            财报披露计划数据列表

        Examples:
            >>> repo = DisclosureDateRepository()
            >>> data = repo.get_by_date_range('20240101', '20240331', ts_code='000001.SZ')
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("end_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("end_date <= %s")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            limit_clause = f"LIMIT {self._enforce_limit(limit)}"
            offset_clause = f"OFFSET {int(offset)}" if offset else ""

            query = f"""
                SELECT
                    ts_code, ann_date, end_date, pre_date, actual_date, modify_date,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                {where_clause}
                ORDER BY end_date DESC, ann_date DESC, ts_code
                {limit_clause}
                {offset_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询财报披露计划数据失败: {e}")
            raise

    def get_by_ts_code(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        按股票代码查询财报披露计划

        Args:
            ts_code: 股票代码
            limit: 限制返回记录数

        Returns:
            财报披露计划数据列表
        """
        query = f"""
            SELECT
                ts_code, ann_date, end_date, pre_date, actual_date, modify_date,
                created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
            ORDER BY end_date DESC, ann_date DESC
            LIMIT %s
        """
        result = self.execute_query(query, (ts_code, limit))
        return [self._row_to_dict(row) for row in result]

    def get_by_end_date(
        self,
        end_date: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期查询财报披露计划（如查询2024年报：20241231）

        Args:
            end_date: 报告期（每个季度最后一天），格式：YYYYMMDD
            limit: 限制返回记录数

        Returns:
            财报披露计划数据列表
        """
        query = f"""
            SELECT
                ts_code, ann_date, end_date, pre_date, actual_date, modify_date,
                created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE end_date = %s
            ORDER BY ann_date DESC, ts_code
            {f"LIMIT {limit}" if limit else ""}
        """
        result = self.execute_query(query, (end_date,))
        return [self._row_to_dict(row) for row in result]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取财报披露计划统计信息

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD

        Returns:
            统计信息字典
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("end_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("end_date <= %s")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(DISTINCT end_date) as period_count,
                    COUNT(CASE WHEN actual_date IS NOT NULL THEN 1 END) as disclosed_count,
                    COUNT(CASE WHEN actual_date IS NULL AND pre_date IS NOT NULL THEN 1 END) as pending_count
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            if result:
                row = result[0]
                return {
                    'total_count': row[0] or 0,
                    'stock_count': row[1] or 0,
                    'period_count': row[2] or 0,
                    'disclosed_count': row[3] or 0,
                    'pending_count': row[4] or 0
                }
            return {
                'total_count': 0,
                'stock_count': 0,
                'period_count': 0,
                'disclosed_count': 0,
                'pending_count': 0
            }

        except Exception as e:
            logger.error(f"获取财报披露计划统计信息失败: {e}")
            raise

    def get_latest_end_date(self) -> Optional[str]:
        """
        获取最新的报告期

        Returns:
            最新报告期（YYYYMMDD格式）
        """
        query = f"""
            SELECT end_date
            FROM {self.TABLE_NAME}
            ORDER BY end_date DESC
            LIMIT 1
        """
        result = self.execute_query(query)
        return result[0][0] if result else None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新财报披露计划数据

        使用ON CONFLICT DO UPDATE实现UPSERT语义

        Args:
            df: 包含财报披露计划数据的DataFrame

        Returns:
            插入/更新的记录数
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                if pd.isna(value):
                    return None
                if isinstance(value, (int, pd.Int64Dtype)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return str(value) if value is not None else None

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('pre_date')),
                    to_python_type(row.get('actual_date')),
                    to_python_type(row.get('modify_date'))
                ))

            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, end_date, pre_date, actual_date, modify_date, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (ts_code, end_date)
                DO UPDATE SET
                    ann_date = EXCLUDED.ann_date,
                    pre_date = EXCLUDED.pre_date,
                    actual_date = EXCLUDED.actual_date,
                    modify_date = EXCLUDED.modify_date,
                    updated_at = NOW()
            """

            # 使用逐条执行来支持 ON CONFLICT
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                count = 0
                for value_tuple in values:
                    cursor.execute(query, value_tuple)
                    count += cursor.rowcount
                conn.commit()
                cursor.close()
                logger.info(f"成功插入/更新 {count} 条财报披露计划数据")
                return count
            except Exception as e:
                conn.rollback()
                logger.error(f"批量插入财报披露计划数据失败: {e}")
                raise
            finally:
                self.db.release_connection(conn)

        except Exception as e:
            logger.error(f"批量插入财报披露计划数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD

        Returns:
            删除的记录数
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE end_date >= %s AND end_date <= %s
        """
        return self.execute_update(query, (start_date, end_date))

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
            'pre_date': row[3],
            'actual_date': row[4],
            'modify_date': row[5],
            'created_at': row[6].isoformat() if row[6] else None,
            'updated_at': row[7].isoformat() if row[7] else None
        }
