"""
股权质押统计 Repository

管理 pledge_stat 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class PledgeStatRepository(BaseRepository):
    """股权质押统计仓库"""

    TABLE_NAME = "pledge_stat"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ PledgeStatRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        min_pledge_ratio: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询股权质押统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            min_pledge_ratio: 最小质押比例（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = PledgeStatRepository()
            >>> data = repo.get_by_date_range('20240101', '20240331')
            >>> data = repo.get_by_date_range('20240101', '20240331', ts_code='000001.SZ')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("end_date >= %s")
                params.append(start_date)
            else:
                conditions.append("end_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("end_date <= %s")
                params.append(end_date)
            else:
                conditions.append("end_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if min_pledge_ratio is not None:
                conditions.append("pledge_ratio >= %s")
                params.append(min_pledge_ratio)

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    ts_code, end_date, pledge_count, unrest_pledge,
                    rest_pledge, total_share, pledge_ratio,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY end_date DESC, pledge_ratio DESC
            """

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'end_date': row[1],
                    'pledge_count': int(row[2]) if row[2] is not None else None,
                    'unrest_pledge': float(row[3]) if row[3] is not None else None,
                    'rest_pledge': float(row[4]) if row[4] is not None else None,
                    'total_share': float(row[5]) if row[5] is not None else None,
                    'pledge_ratio': float(row[6]) if row[6] is not None else None,
                    'created_at': row[7].isoformat() + 'Z' if row[7] else None,
                    'updated_at': row[8].isoformat() + 'Z' if row[8] else None
                })

            logger.debug(f"查询到 {len(data)} 条股权质押统计数据")
            return data

        except Exception as e:
            logger.error(f"查询股权质押统计数据失败: {e}")
            raise QueryError(
                "数据查询失败",
                error_code="PLEDGE_STAT_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取股权质押统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = PledgeStatRepository()
            >>> stats = repo.get_statistics('20240101', '20240331')
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

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(pledge_ratio) as avg_pledge_ratio,
                    MAX(pledge_ratio) as max_pledge_ratio,
                    SUM(pledge_count) as total_pledge_count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            row = result[0] if result else None

            if row:
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'avg_pledge_ratio': float(row[2]) if row[2] is not None else 0.0,
                    'max_pledge_ratio': float(row[3]) if row[3] is not None else 0.0,
                    'total_pledge_count': int(row[4]) if row[4] else 0
                }
            else:
                return {
                    'total_count': 0,
                    'stock_count': 0,
                    'avg_pledge_ratio': 0.0,
                    'max_pledge_ratio': 0.0,
                    'total_pledge_count': 0
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "统计信息查询失败",
                error_code="PLEDGE_STAT_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_end_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新的截止日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新截止日期（YYYYMMDD），如果没有数据返回 None

        Examples:
            >>> repo = PledgeStatRepository()
            >>> latest_date = repo.get_latest_end_date()
            >>> latest_date = repo.get_latest_end_date('000001.SZ')
        """
        try:
            if ts_code:
                query = f"""
                    SELECT MAX(end_date)
                    FROM {self.TABLE_NAME}
                    WHERE ts_code = %s
                """
                result = self.execute_query(query, (ts_code,))
            else:
                query = f"""
                    SELECT MAX(end_date)
                    FROM {self.TABLE_NAME}
                """
                result = self.execute_query(query, ())

            latest_date = result[0][0] if result and result[0][0] else None

            logger.debug(f"最新截止日期: {latest_date}")
            return latest_date

        except Exception as e:
            logger.error(f"获取最新截止日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新股权质押统计数据（UPSERT）

        Args:
            df: 包含股权质押统计数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = PledgeStatRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将 pandas/numpy 类型转换为 Python 原生类型
            def to_python_type(value):
                """
                将 pandas/numpy 类型转换为 Python 原生类型

                关键问题：psycopg2 无法直接处理 numpy 类型
                必须转换为 Python 原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换 numpy 整数类型为 Python int
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                # 转换 numpy 浮点类型为 Python float
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('pledge_count')),
                    to_python_type(row.get('unrest_pledge')),
                    to_python_type(row.get('rest_pledge')),
                    to_python_type(row.get('total_share')),
                    to_python_type(row.get('pledge_ratio'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, end_date, pledge_count, unrest_pledge,
                    rest_pledge, total_share, pledge_ratio,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (ts_code, end_date)
                DO UPDATE SET
                    pledge_count = EXCLUDED.pledge_count,
                    unrest_pledge = EXCLUDED.unrest_pledge,
                    rest_pledge = EXCLUDED.rest_pledge,
                    total_share = EXCLUDED.total_share,
                    pledge_ratio = EXCLUDED.pledge_ratio,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条股权质押统计数据")
            return count

        except Exception as e:
            logger.error(f"批量插入股权质押统计数据失败: {e}")
            raise QueryError(
                "批量插入数据失败",
                error_code="PLEDGE_STAT_UPSERT_FAILED",
                reason=str(e)
            )

    def get_by_stock(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        获取指定股票的股权质押统计数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = PledgeStatRepository()
            >>> data = repo.get_by_stock('000001.SZ', limit=50)
        """
        return self.get_by_date_range(
            ts_code=ts_code,
            limit=limit
        )

    def get_high_pledge_stocks(
        self,
        end_date: str,
        min_ratio: float = 50.0,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取高质押比例股票

        Args:
            end_date: 截止日期，格式：YYYYMMDD
            min_ratio: 最小质押比例（默认50%）
            limit: 返回记录数限制

        Returns:
            数据列表（按pledge_ratio降序排序）

        Examples:
            >>> repo = PledgeStatRepository()
            >>> data = repo.get_high_pledge_stocks('20240331', min_ratio=60.0, limit=50)
        """
        try:
            query = f"""
                SELECT
                    ts_code, end_date, pledge_count, unrest_pledge,
                    rest_pledge, total_share, pledge_ratio,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE end_date = %s AND pledge_ratio >= %s
                ORDER BY pledge_ratio DESC, ts_code
                LIMIT %s
            """

            result = self.execute_query(query, (end_date, min_ratio, limit))

            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'end_date': row[1],
                    'pledge_count': int(row[2]) if row[2] is not None else None,
                    'unrest_pledge': float(row[3]) if row[3] is not None else None,
                    'rest_pledge': float(row[4]) if row[4] is not None else None,
                    'total_share': float(row[5]) if row[5] is not None else None,
                    'pledge_ratio': float(row[6]) if row[6] is not None else None,
                    'created_at': row[7].isoformat() + 'Z' if row[7] else None,
                    'updated_at': row[8].isoformat() + 'Z' if row[8] else None
                })

            logger.debug(f"查询到 {len(data)} 条高质押比例股票")
            return data

        except Exception as e:
            logger.error(f"查询高质押比例股票失败: {e}")
            raise QueryError(
                "查询高质押比例股票失败",
                error_code="PLEDGE_STAT_HIGH_PLEDGE_FAILED",
                reason=str(e)
            )
