"""
股票回购数据Repository

管理repurchase表的数据访问
"""

import pandas as pd
from typing import List, Dict, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class RepurchaseRepository(BaseRepository):
    """股票回购数据Repository"""

    TABLE_NAME = "repurchase"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ RepurchaseRepository initialized")

    def get_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        proc: Optional[str] = None
    ) -> int:
        """
        获取符合条件的记录总数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            proc: 回购进度（可选）

        Returns:
            记录总数
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]
            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)
            if proc:
                query += " AND proc = %s"
                params.append(proc)
            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"获取回购记录总数失败: {e}")
            return 0

    def get_by_date_range(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        proc: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询回购数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            proc: 回购进度（可选，如：完成、实施、股东大会通过）
            limit: 限制返回记录数

        Returns:
            回购数据列表

        Examples:
            >>> repo = RepurchaseRepository()
            >>> data = repo.get_by_date_range('20240101', '20241231')
            >>> data = repo.get_by_date_range(ts_code='600000.SH', proc='完成')
        """
        try:
            query = f"""
                SELECT ts_code, ann_date, end_date, proc, exp_date,
                       vol, amount, high_limit, low_limit,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE ann_date >= %s AND ann_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if proc:
                query += " AND proc = %s"
                params.append(proc)

            query += " ORDER BY ann_date DESC, ts_code"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            if offset:
                query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询回购数据失败: {e}")
            raise QueryError(
                "回购数据查询失败",
                error_code="REPURCHASE_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取回购数据统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = RepurchaseRepository()
            >>> stats = repo.get_statistics('20240101', '20241231')
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    SUM(vol) as total_vol,
                    SUM(amount) as total_amount,
                    AVG(amount) as avg_amount,
                    MAX(amount) as max_amount,
                    MIN(amount) as min_amount,
                    AVG(high_limit) as avg_high_limit,
                    AVG(low_limit) as avg_low_limit
                FROM {self.TABLE_NAME}
                WHERE ann_date >= %s AND ann_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            if result:
                row = result[0]
                return {
                    'total_count': row[0] or 0,
                    'stock_count': row[1] or 0,
                    'total_vol': float(row[2]) if row[2] else 0.0,
                    'total_amount': float(row[3]) if row[3] else 0.0,
                    'avg_amount': float(row[4]) if row[4] else 0.0,
                    'max_amount': float(row[5]) if row[5] else 0.0,
                    'min_amount': float(row[6]) if row[6] else 0.0,
                    'avg_high_limit': float(row[7]) if row[7] else 0.0,
                    'avg_low_limit': float(row[8]) if row[8] else 0.0
                }

            return {
                'total_count': 0,
                'stock_count': 0,
                'total_vol': 0.0,
                'total_amount': 0.0,
                'avg_amount': 0.0,
                'max_amount': 0.0,
                'min_amount': 0.0,
                'avg_high_limit': 0.0,
                'avg_low_limit': 0.0
            }

        except Exception as e:
            logger.error(f"获取回购统计信息失败: {e}")
            raise QueryError(
                "回购统计查询失败",
                error_code="REPURCHASE_STATISTICS_FAILED",
                reason=str(e)
            )

    def get_latest_ann_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新公告日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新公告日期（YYYYMMDD格式），如果没有数据返回None

        Examples:
            >>> repo = RepurchaseRepository()
            >>> latest_date = repo.get_latest_ann_date()
            >>> latest_date = repo.get_latest_ann_date(ts_code='600000.SH')
        """
        try:
            query = f"SELECT MAX(ann_date) FROM {self.TABLE_NAME}"
            params = []

            if ts_code:
                query += " WHERE ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params) if params else None)

            if result and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新公告日期失败: {e}")
            raise QueryError(
                "获取最新公告日期失败",
                error_code="REPURCHASE_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新回购数据

        Args:
            df: 包含回购数据的DataFrame

        Returns:
            受影响的记录数

        Examples:
            >>> repo = RepurchaseRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
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

            # 准备UPSERT查询
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, end_date, proc, exp_date, vol, amount, high_limit, low_limit, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ts_code, ann_date)
                DO UPDATE SET
                    end_date = EXCLUDED.end_date,
                    proc = EXCLUDED.proc,
                    exp_date = EXCLUDED.exp_date,
                    vol = EXCLUDED.vol,
                    amount = EXCLUDED.amount,
                    high_limit = EXCLUDED.high_limit,
                    low_limit = EXCLUDED.low_limit,
                    updated_at = NOW()
            """

            # 准备插入数据（对每个字段应用类型转换）
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('proc')),
                    to_python_type(row.get('exp_date')),
                    to_python_type(row.get('vol')),
                    to_python_type(row.get('amount')),
                    to_python_type(row.get('high_limit')),
                    to_python_type(row.get('low_limit'))
                ))

            # 执行批量插入
            count = self.execute_batch(query, values)

            logger.info(f"成功插入/更新 {count} 条回购记录")
            return count

        except Exception as e:
            logger.error(f"批量插入回购数据失败: {e}")
            raise QueryError(
                "批量插入回购数据失败",
                error_code="REPURCHASE_BULK_UPSERT_FAILED",
                reason=str(e)
            )

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
            >>> repo = RepurchaseRepository()
            >>> count = repo.delete_by_date_range('20240101', '20241231')
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            count = self.execute_update(query, tuple(params))

            logger.info(f"删除了 {count} 条回购记录")
            return count

        except Exception as e:
            logger.error(f"删除回购数据失败: {e}")
            raise QueryError(
                "删除回购数据失败",
                error_code="REPURCHASE_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, ann_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            True 如果存在，否则 False

        Examples:
            >>> repo = RepurchaseRepository()
            >>> exists = repo.exists_by_date('20240115')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date = %s"
            params = [ann_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查回购数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取记录总数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            记录总数

        Examples:
            >>> repo = RepurchaseRepository()
            >>> count = repo.get_record_count('20240101', '20241231')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取回购记录数失败: {e}")
            raise QueryError(
                "获取回购记录数失败",
                error_code="REPURCHASE_COUNT_FAILED",
                reason=str(e)
            )

    def get_by_proc(
        self,
        proc: str,
        start_date: str = '19900101',
        end_date: str = '29991231',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按回购进度查询数据

        Args:
            proc: 回购进度（如：完成、实施、股东大会通过）
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 限制返回记录数

        Returns:
            回购数据列表

        Examples:
            >>> repo = RepurchaseRepository()
            >>> data = repo.get_by_proc('完成', limit=50)
        """
        return self.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            proc=proc,
            limit=limit
        )

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'end_date': row[2],
            'proc': row[3],
            'exp_date': row[4],
            'vol': float(row[5]) if row[5] is not None else None,
            'amount': float(row[6]) if row[6] is not None else None,
            'high_limit': float(row[7]) if row[7] is not None else None,
            'low_limit': float(row[8]) if row[8] is not None else None,
            'created_at': row[9].isoformat() if row[9] else None,
            'updated_at': row[10].isoformat() if row[10] else None
        }
