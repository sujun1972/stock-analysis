"""
东方财富板块成分 Repository

管理 dc_member 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class DcMemberRepository(BaseRepository):
    """东方财富板块成分仓库"""

    TABLE_NAME = "dc_member"

    SORTABLE_COLUMNS = {'trade_date', 'ts_code', 'con_code', 'name'}

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ DcMemberRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> List[Dict]:
        """
        按日期范围查询板块成分数据（支持分页和后端排序）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码，如 'BK1184.DC'（可选）
            con_code: 成分股票代码，如 '002117.SZ'（可选）
            trade_date: 单日查询，优先级高于 start/end，格式：YYYYMMDD
            page: 页码，从 1 开始
            page_size: 每页记录数
            sort_by: 排序字段（白名单校验）
            sort_order: 排序方向，'asc' 或 'desc'

        Returns:
            数据列表

        Examples:
            >>> repo = DcMemberRepository()
            >>> data = repo.get_by_date_range(trade_date='20250102')
            >>> data = repo.get_by_date_range('20250101', '20250131', ts_code='BK1184.DC')
            >>> data = repo.get_by_date_range(trade_date='20250102', page=2, page_size=100)
        """
        try:
            conditions = []
            params = []

            if trade_date:
                conditions.append("trade_date = %s")
                params.append(trade_date)
            else:
                if start_date:
                    conditions.append("trade_date >= %s")
                    params.append(start_date)
                else:
                    conditions.append("trade_date >= %s")
                    params.append('19900101')

                if end_date:
                    conditions.append("trade_date <= %s")
                    params.append(end_date)
                else:
                    conditions.append("trade_date <= %s")
                    params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if con_code:
                conditions.append("con_code = %s")
                params.append(con_code)

            where_clause = " AND ".join(conditions)

            # 白名单校验排序字段
            order_field = sort_by if sort_by and sort_by in self.SORTABLE_COLUMNS else 'trade_date'
            order_dir = 'ASC' if sort_order and sort_order.lower() == 'asc' else 'DESC'
            order_clause = f"ORDER BY {order_field} {order_dir} NULLS LAST"

            offset = (page - 1) * page_size

            query = f"""
                SELECT
                    trade_date, ts_code, con_code, name,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            params.append(page_size)
            params.append(offset)

            result = self.execute_query(query, tuple(params))

            data = []
            for row in result:
                data.append({
                    'trade_date': row[0],
                    'ts_code': row[1],
                    'con_code': row[2],
                    'name': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'updated_at': row[5].isoformat() if row[5] else None
                })

            logger.debug(f"查询到 {len(data)} 条板块成分数据")
            return data

        except Exception as e:
            logger.error(f"查询板块成分数据失败: {e}")
            raise QueryError(
                "板块成分数据查询失败",
                error_code="DC_MEMBER_QUERY_FAILED",
                reason=str(e)
            )

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None
    ) -> int:
        """
        查询满足条件的记录总数（用于分页）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）
            con_code: 成分股票代码（可选）
            trade_date: 单日查询，优先级高于 start/end，格式：YYYYMMDD

        Returns:
            记录总数

        Examples:
            >>> repo = DcMemberRepository()
            >>> count = repo.get_total_count(trade_date='20250102')
        """
        try:
            conditions = []
            params = []

            if trade_date:
                conditions.append("trade_date = %s")
                params.append(trade_date)
            else:
                if start_date:
                    conditions.append("trade_date >= %s")
                    params.append(start_date)
                else:
                    conditions.append("trade_date >= %s")
                    params.append('19900101')

                if end_date:
                    conditions.append("trade_date <= %s")
                    params.append(end_date)
                else:
                    conditions.append("trade_date <= %s")
                    params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if con_code:
                conditions.append("con_code = %s")
                params.append(con_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"查询记录总数失败: {e}")
            return 0

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None
    ) -> Dict:
        """
        获取板块成分统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）
            trade_date: 单日查询，优先级高于 start/end，格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = DcMemberRepository()
            >>> stats = repo.get_statistics(trade_date='20250102')
            >>> stats = repo.get_statistics('20250101', '20250131', ts_code='BK1184.DC')
        """
        try:
            conditions = []
            params = []

            if trade_date:
                conditions.append("trade_date = %s")
                params.append(trade_date)
            else:
                if start_date:
                    conditions.append("trade_date >= %s")
                    params.append(start_date)
                else:
                    conditions.append("trade_date >= %s")
                    params.append('19900101')

                if end_date:
                    conditions.append("trade_date <= %s")
                    params.append(end_date)
                else:
                    conditions.append("trade_date <= %s")
                    params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as board_count,
                    COUNT(DISTINCT con_code) as stock_count,
                    COUNT(DISTINCT trade_date) as date_count,
                    MIN(trade_date) as earliest_date,
                    MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_records': row[0] or 0,
                    'board_count': row[1] or 0,
                    'stock_count': row[2] or 0,
                    'date_count': row[3] or 0,
                    'earliest_date': row[4],
                    'latest_date': row[5]
                }

            return {
                'total_records': 0,
                'board_count': 0,
                'stock_count': 0,
                'date_count': 0,
                'earliest_date': None,
                'latest_date': None
            }

        except Exception as e:
            logger.error(f"获取板块成分统计信息失败: {e}")
            raise QueryError(
                "获取板块成分统计信息失败",
                error_code="DC_MEMBER_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYYMMDD格式）

        Examples:
            >>> repo = DcMemberRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        try:
            query = f"""
                SELECT MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
            """

            result = self.execute_query(query)

            if result and len(result) > 0 and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新板块成分数据（UPSERT）

        Args:
            df: 包含板块成分数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = DcMemberRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            def to_python_type(value):
                """将pandas/numpy类型转换为Python原生类型"""
                if pd.isna(value):
                    return None
                if isinstance(value, (int, float, str)):
                    return value
                if hasattr(value, 'item'):
                    return value.item()
                return str(value)

            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('con_code')),
                    to_python_type(row.get('name'))
                ))

            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, ts_code, con_code, name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (trade_date, ts_code, con_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条板块成分数据")
            return count

        except Exception as e:
            logger.error(f"批量插入板块成分数据失败: {e}")
            raise QueryError(
                "批量插入板块成分数据失败",
                error_code="DC_MEMBER_BULK_UPSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = DcMemberRepository()
            >>> count = repo.delete_by_date_range('20250101', '20250131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """

            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除了 {count} 条板块成分数据 ({start_date} ~ {end_date})")
            return count

        except Exception as e:
            logger.error(f"删除板块成分数据失败: {e}")
            raise QueryError(
                "删除板块成分数据失败",
                error_code="DC_MEMBER_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）

        Returns:
            是否存在数据

        Examples:
            >>> repo = DcMemberRepository()
            >>> exists = repo.exists_by_date('20250102')
            >>> exists = repo.exists_by_date('20250102', ts_code='BK1184.DC')
        """
        try:
            if ts_code:
                query = f"""
                    SELECT EXISTS(
                        SELECT 1 FROM {self.TABLE_NAME}
                        WHERE trade_date = %s AND ts_code = %s
                    )
                """
                result = self.execute_query(query, (trade_date, ts_code))
            else:
                query = f"""
                    SELECT EXISTS(
                        SELECT 1 FROM {self.TABLE_NAME}
                        WHERE trade_date = %s
                    )
                """
                result = self.execute_query(query, (trade_date,))

            return bool(result[0][0]) if result else False

        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            return False

