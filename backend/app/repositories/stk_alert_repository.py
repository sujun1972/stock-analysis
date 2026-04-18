"""
交易所重点提示证券 Repository

管理 stk_alert 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class StkAlertRepository(BaseRepository):
    """交易所重点提示证券仓库"""

    TABLE_NAME = "stk_alert"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkAlertRepository initialized")

    def get_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
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
        conditions = []
        params = []
        if start_date:
            conditions.append("start_date >= %s")
            params.append(start_date)
        else:
            conditions.append("start_date >= %s")
            params.append('19900101')
        if end_date:
            conditions.append("start_date <= %s")
            params.append(end_date)
        else:
            conditions.append("start_date <= %s")
            params.append('29991231')
        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        where_clause = " AND ".join(conditions)
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
        result = self.execute_query(query, tuple(params))
        return result[0][0] if result else 0

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        alert_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询交易所重点提示证券

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            alert_type: 提示类型（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = StkAlertRepository()
            >>> data = repo.get_by_date_range('20260301', '20260331')
            >>> data = repo.get_by_date_range('20260301', '20260331', ts_code='000001.SZ')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("start_date >= %s")
                params.append(start_date)
            else:
                conditions.append("start_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("start_date <= %s")
                params.append(end_date)
            else:
                conditions.append("start_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if alert_type:
                conditions.append("type = %s")
                params.append(alert_type)

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    ts_code, name, start_date, end_date, type,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY start_date DESC, ts_code
            """

            query += " LIMIT %s"
            params.append(self._enforce_limit(limit))

            if offset:
                query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'name': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'type': row[4],
                    'created_at': row[5].isoformat() + 'Z' if row[5] else None,
                    'updated_at': row[6].isoformat() + 'Z' if row[6] else None
                })

            logger.debug(f"查询到 {len(data)} 条交易所重点提示证券数据")
            return data

        except Exception as e:
            logger.error(f"查询交易所重点提示证券数据失败: {e}")
            raise QueryError(
                "数据查询失败",
                error_code="STK_ALERT_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取交易所重点提示证券统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkAlertRepository()
            >>> stats = repo.get_statistics('20260301', '20260331')
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("start_date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("start_date <= %s")
                params.append(end_date)

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(DISTINCT type) as type_count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            row = result[0] if result else None

            if row:
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'type_count': int(row[2]) if row[2] else 0
                }
            else:
                return {
                    'total_count': 0,
                    'stock_count': 0,
                    'type_count': 0
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "统计信息查询失败",
                error_code="STK_ALERT_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_start_date(self) -> Optional[str]:
        """
        获取最新的提示起始日期

        Returns:
            最新提示起始日期（YYYYMMDD），如果没有数据返回 None

        Examples:
            >>> repo = StkAlertRepository()
            >>> latest_date = repo.get_latest_start_date()
        """
        try:
            query = f"""
                SELECT MAX(start_date)
                FROM {self.TABLE_NAME}
            """

            result = self.execute_query(query, ())
            latest_date = result[0][0] if result and result[0][0] else None

            logger.debug(f"最新提示起始日期: {latest_date}")
            return latest_date

        except Exception as e:
            logger.error(f"获取最新提示起始日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新交易所重点提示证券数据（UPSERT）

        Args:
            df: 包含交易所重点提示证券数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkAlertRepository()
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
                必须��换为 Python 原生类型（int, float, None）
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
                    to_python_type(row.get('name')),
                    to_python_type(row.get('start_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('type'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, name, start_date, end_date, type,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (ts_code, start_date)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    end_date = EXCLUDED.end_date,
                    type = EXCLUDED.type,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条交易所重点提示证券数据")
            return count

        except Exception as e:
            logger.error(f"批量插入交易所重点提示证券数据失败: {e}")
            raise QueryError(
                "批量插入数据失败",
                error_code="STK_ALERT_UPSERT_FAILED",
                reason=str(e)
            )

    def get_by_stock(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        获取指定股票的交易所重点提示证券数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = StkAlertRepository()
            >>> data = repo.get_by_stock('000001.SZ', limit=50)
        """
        return self.get_by_date_range(
            ts_code=ts_code,
            limit=limit
        )

    def get_active_alerts(
        self,
        current_date: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取当前仍在有效期内的重点提示证券

        Args:
            current_date: 当前日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            数据列表（按start_date降序排序）

        Examples:
            >>> repo = StkAlertRepository()
            >>> data = repo.get_active_alerts('20260315', limit=50)
        """
        try:
            query = f"""
                SELECT
                    ts_code, name, start_date, end_date, type,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE start_date <= %s AND end_date >= %s
                ORDER BY start_date DESC, ts_code
                LIMIT %s
            """

            result = self.execute_query(query, (current_date, current_date, limit))

            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'name': row[1],
                    'start_date': row[2],
                    'end_date': row[3],
                    'type': row[4],
                    'created_at': row[5].isoformat() + 'Z' if row[5] else None,
                    'updated_at': row[6].isoformat() + 'Z' if row[6] else None
                })

            logger.debug(f"查询到 {len(data)} 条当前有效的重点提示证券")
            return data

        except Exception as e:
            logger.error(f"查询当前有效的重点提示证券失败: {e}")
            raise QueryError(
                "查询当前有效的重点提示证券失败",
                error_code="STK_ALERT_ACTIVE_FAILED",
                reason=str(e)
            )
