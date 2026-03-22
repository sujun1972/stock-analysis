"""
限售股解禁数据 Repository

管理 share_float 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class ShareFloatRepository(BaseRepository):
    """限售股解禁数据 Repository"""

    TABLE_NAME = "share_float"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ ShareFloatRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询限售股解禁数据

        Args:
            start_date: 开始日期 (解禁日期), 格式：YYYYMMDD
            end_date: 结束日期 (解禁日期), 格式：YYYYMMDD
            ts_code: 股票代码（可选）
            ann_date: 公告日期（可选）
            float_date: 解禁日期（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = ShareFloatRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("float_date >= %s")
                params.append(start_date)
            else:
                conditions.append("float_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("float_date <= %s")
                params.append(end_date)
            else:
                conditions.append("float_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if ann_date:
                conditions.append("ann_date = %s")
                params.append(ann_date)

            if float_date:
                conditions.append("float_date = %s")
                params.append(float_date)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    float_date,
                    float_share,
                    float_ratio,
                    holder_name,
                    share_type,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY float_date DESC, ts_code ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询限售股解禁数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取限售股解禁统计信息

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = ShareFloatRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("float_date >= %s")
                params.append(start_date)
            else:
                conditions.append("float_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("float_date <= %s")
                params.append(end_date)
            else:
                conditions.append("float_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as total_stocks,
                    SUM(float_share) as total_float_share,
                    AVG(float_ratio) as avg_float_ratio,
                    MAX(float_share) as max_float_share,
                    MAX(float_ratio) as max_float_ratio
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_records': row[0] or 0,
                    'total_stocks': row[1] or 0,
                    'total_float_share': float(row[2]) if row[2] else 0.0,
                    'avg_float_ratio': float(row[3]) if row[3] else 0.0,
                    'max_float_share': float(row[4]) if row[4] else 0.0,
                    'max_float_ratio': float(row[5]) if row[5] else 0.0,
                }

            return {
                'total_records': 0,
                'total_stocks': 0,
                'total_float_share': 0.0,
                'avg_float_ratio': 0.0,
                'max_float_share': 0.0,
                'max_float_ratio': 0.0,
            }

        except Exception as e:
            logger.error(f"获取限售股解禁统计信息失败: {e}")
            raise

    def get_latest_float_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新解禁日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新解禁日期 YYYYMMDD，如果没有数据则返回 None

        Examples:
            >>> repo = ShareFloatRepository()
            >>> latest_date = repo.get_latest_float_date()
        """
        try:
            query = f"""
                SELECT MAX(float_date) as latest_date
                FROM {self.TABLE_NAME}
            """

            params = []
            if ts_code:
                query = f"""
                    SELECT MAX(float_date) as latest_date
                    FROM {self.TABLE_NAME}
                    WHERE ts_code = %s
                """
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0 and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新解禁日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新限售股解禁数据

        Args:
            df: 包含限售股解禁数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = ShareFloatRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                ⚠️ 关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换numpy整数/浮点类型为Python类型
                if isinstance(value, (pd.Int64Dtype, int, float)) or hasattr(value, 'item'):
                    try:
                        if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                            return float(value)
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    row.get('ts_code'),
                    row.get('ann_date'),
                    row.get('float_date'),
                    to_python_type(row.get('float_share')),
                    to_python_type(row.get('float_ratio')),
                    row.get('holder_name'),
                    row.get('share_type'),
                ))

            # 执行批量 UPSERT
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, float_date, float_share, float_ratio, holder_name, share_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ts_code, ann_date, float_date, holder_name)
                DO UPDATE SET
                    float_share = EXCLUDED.float_share,
                    float_ratio = EXCLUDED.float_ratio,
                    share_type = EXCLUDED.share_type,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条限售股解禁记录")

            return count

        except Exception as e:
            logger.error(f"批量插入限售股解禁数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期（解禁日期），格式：YYYYMMDD
            end_date: 结束日期（解禁日期），格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = ShareFloatRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            conditions = ["float_date >= %s", "float_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            count = self.execute_update(query, tuple(params))
            logger.info(f"成功删除 {count} 条限售股解禁记录")

            return count

        except Exception as e:
            logger.error(f"删除限售股解禁数据失败: {e}")
            raise

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
            'float_date': row[2],
            'float_share': float(row[3]) if row[3] is not None else None,
            'float_ratio': float(row[4]) if row[4] is not None else None,
            'holder_name': row[5],
            'share_type': row[6],
            'created_at': row[7].isoformat() + 'Z' if row[7] else None,
            'updated_at': row[8].isoformat() + 'Z' if row[8] else None,
        }
