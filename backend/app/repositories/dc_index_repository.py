"""
东方财富板块数据 Repository

管理 dc_index 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class DcIndexRepository(BaseRepository):
    """东方财富板块数据仓库"""

    TABLE_NAME = "dc_index"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ DcIndexRepository initialized")

    SORTABLE_COLUMNS = {'pct_change', 'leading_pct', 'turnover_rate', 'total_mv', 'up_num', 'down_num'}

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        idx_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询板块数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）
            name: 板块名称（可选，模糊匹配）
            idx_type: 板块类型（可选，如 '概念板块'、'行业板块'、'地域板块'）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = DcIndexRepository()
            >>> data = repo.get_by_date_range('20250101', '20250131')
            >>> data = repo.get_by_date_range('20250101', '20250131', idx_type='概念板块')
        """
        try:
            conditions = []
            params = []

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

            if name:
                conditions.append("name ILIKE %s")
                params.append(f"%{name}%")

            if idx_type:
                conditions.append("idx_type = %s")
                params.append(idx_type)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code, trade_date, name, leading_stock, leading_code,
                    pct_change, leading_pct, total_mv, turnover_rate,
                    up_num, down_num, idx_type, level,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, pct_change DESC
            """

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))

            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'trade_date': row[1],
                    'name': row[2],
                    'leading_stock': row[3],
                    'leading_code': row[4],
                    'pct_change': row[5],
                    'leading_pct': row[6],
                    'total_mv': row[7],
                    'turnover_rate': row[8],
                    'up_num': row[9],
                    'down_num': row[10],
                    'idx_type': row[11],
                    'level': row[12],
                    'created_at': row[13].isoformat() if row[13] else None,
                    'updated_at': row[14].isoformat() if row[14] else None
                })

            logger.debug(f"查询到 {len(data)} 条板块数据")
            return data

        except Exception as e:
            logger.error(f"查询板块数据失败: {e}")
            raise QueryError(
                "板块数据查询失败",
                error_code="DC_INDEX_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_trade_date(
        self,
        trade_date: str,
        idx_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict:
        """
        按单日交易日期分页查询板块数据（支持后端排序）

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            idx_type: 板块类型（可选）
            page: 页码（从1开始）
            page_size: 每页记录数
            sort_by: 排序字段（白名单：pct_change/leading_pct/turnover_rate/total_mv/up_num/down_num）
            sort_order: 排序方向（asc/desc）

        Returns:
            包含 items、total、trade_date 的字典

        Examples:
            >>> repo = DcIndexRepository()
            >>> result = repo.get_by_trade_date('20250326', idx_type='概念板块', page=1)
        """
        try:
            conditions = ["trade_date = %s"]
            params: list = [trade_date]

            if idx_type:
                conditions.append("idx_type = %s")
                params.append(idx_type)

            where_clause = " AND ".join(conditions)

            # 排序白名单防注入
            if sort_by and sort_by in self.SORTABLE_COLUMNS:
                order = 'ASC' if sort_order and sort_order.lower() == 'asc' else 'DESC'
                order_clause = f"ORDER BY {sort_by} {order} NULLS LAST"
            else:
                order_clause = "ORDER BY pct_change DESC NULLS LAST"

            count_query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
            count_result = self.execute_query(count_query, tuple(params))
            total = count_result[0][0] if count_result else 0

            offset = (page - 1) * page_size
            data_query = f"""
                SELECT
                    ts_code, trade_date, name, leading_stock, leading_code,
                    pct_change, leading_pct, total_mv, turnover_rate,
                    up_num, down_num, idx_type, level
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            data_params = tuple(params) + (page_size, offset)
            result = self.execute_query(data_query, data_params)

            items = []
            for row in result:
                items.append({
                    'ts_code': row[0],
                    'trade_date': row[1],
                    'name': row[2],
                    'leading_stock': row[3],
                    'leading_code': row[4],
                    'pct_change': float(row[5]) if row[5] is not None else None,
                    'leading_pct': float(row[6]) if row[6] is not None else None,
                    'total_mv': float(row[7]) if row[7] is not None else None,
                    'turnover_rate': float(row[8]) if row[8] is not None else None,
                    'up_num': row[9],
                    'down_num': row[10],
                    'idx_type': row[11],
                    'level': row[12],
                })

            logger.debug(f"查询到 {len(items)} 条板块数据（共 {total} 条）")
            return {'items': items, 'total': total, 'trade_date': trade_date}

        except Exception as e:
            logger.error(f"查询板块数据失败: {e}")
            raise QueryError(
                "板块数据查询失败",
                error_code="DC_INDEX_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        idx_type: Optional[str] = None
    ) -> Dict:
        """
        获取板块数据统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）
            idx_type: 板块类型（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = DcIndexRepository()
            >>> stats = repo.get_statistics('20250101', '20250131')
        """
        try:
            conditions = []
            params = []

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

            if idx_type:
                conditions.append("idx_type = %s")
                params.append(idx_type)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as board_count,
                    COUNT(DISTINCT trade_date) as date_count,
                    MIN(trade_date) as earliest_date,
                    MAX(trade_date) as latest_date,
                    AVG(pct_change) as avg_pct_change
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_records': row[0] or 0,
                    'board_count': row[1] or 0,
                    'date_count': row[2] or 0,
                    'earliest_date': row[3],
                    'latest_date': row[4],
                    'avg_pct_change': float(row[5]) if row[5] is not None else None
                }

            return {
                'total_records': 0,
                'board_count': 0,
                'date_count': 0,
                'earliest_date': None,
                'latest_date': None,
                'avg_pct_change': None
            }

        except Exception as e:
            logger.error(f"获取板块数据统计信息失败: {e}")
            raise QueryError(
                "获取板块数据统计信息失败",
                error_code="DC_INDEX_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYYMMDD格式）

        Examples:
            >>> repo = DcIndexRepository()
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
        批量插入/更新板块数据（UPSERT）

        Args:
            df: 包含板块数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = DcIndexRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                ⚠️ 关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, str, None）
                """
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
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('leading_stock')),
                    to_python_type(row.get('leading_code')),
                    to_python_type(row.get('pct_change')),
                    to_python_type(row.get('leading_pct')),
                    to_python_type(row.get('total_mv')),
                    to_python_type(row.get('turnover_rate')),
                    to_python_type(row.get('up_num')),
                    to_python_type(row.get('down_num')),
                    to_python_type(row.get('idx_type')),
                    to_python_type(row.get('level'))
                ))

            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, trade_date, name, leading_stock, leading_code,
                 pct_change, leading_pct, total_mv, turnover_rate,
                 up_num, down_num, idx_type, level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    leading_stock = EXCLUDED.leading_stock,
                    leading_code = EXCLUDED.leading_code,
                    pct_change = EXCLUDED.pct_change,
                    leading_pct = EXCLUDED.leading_pct,
                    total_mv = EXCLUDED.total_mv,
                    turnover_rate = EXCLUDED.turnover_rate,
                    up_num = EXCLUDED.up_num,
                    down_num = EXCLUDED.down_num,
                    idx_type = EXCLUDED.idx_type,
                    level = EXCLUDED.level,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条板块数据")
            return count

        except Exception as e:
            logger.error(f"批量插入板块数据失败: {e}")
            raise QueryError(
                "批量插入板块数据失败",
                error_code="DC_INDEX_BULK_UPSERT_FAILED",
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
            >>> repo = DcIndexRepository()
            >>> count = repo.delete_by_date_range('20250101', '20250131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """

            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除了 {count} 条板块数据 ({start_date} ~ {end_date})")
            return count

        except Exception as e:
            logger.error(f"删除板块数据失败: {e}")
            raise QueryError(
                "删除板块数据失败",
                error_code="DC_INDEX_DELETE_FAILED",
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
            >>> repo = DcIndexRepository()
            >>> exists = repo.exists_by_date('20250102')
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

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取指定日期范围的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = DcIndexRepository()
            >>> count = repo.get_record_count('20250101', '20250131')
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0
