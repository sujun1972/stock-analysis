"""
中央结算系统持股明细 Repository

管理 ccass_hold_detail 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class CcassHoldDetailRepository(BaseRepository):
    """中央结算系统持股明细仓库"""

    TABLE_NAME = "ccass_hold_detail"

    SORTABLE_COLUMNS = {'trade_date', 'ts_code', 'col_shareholding', 'col_shareholding_percent'}

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CcassHoldDetailRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        col_participant_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> List[Dict]:
        """
        按日期范围查询中央结算系统持股明细数据（分页+排序）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码，如 '00960.HK'（可选）
            col_participant_id: 参与者编号，如 'B01777'（可选）
            page: 页码（从1开始）
            page_size: 每页记录数
            sort_by: 排序字段（白名单校验）
            sort_order: 排序方向 asc/desc

        Returns:
            数据列表

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='00960.HK')
        """
        try:
            # 构建WHERE条件
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)
            if col_participant_id:
                conditions.append("col_participant_id = %s")
                params.append(col_participant_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 排序（白名单防注入）
            order = 'DESC' if (sort_order or '').lower() != 'asc' else 'ASC'
            if sort_by and sort_by in self.SORTABLE_COLUMNS:
                order_clause = f"ORDER BY {sort_by} {order} NULLS LAST"
            else:
                order_clause = "ORDER BY trade_date DESC, ts_code, col_shareholding DESC"

            # 分页
            offset = (page - 1) * page_size

            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    col_participant_id,
                    col_participant_name,
                    col_shareholding,
                    col_shareholding_percent,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                {order_clause}
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询中央结算系统持股明细数据失败: {e}")
            raise QueryError(
                "查询中央结算系统持股明细数据失败",
                error_code="CCASS_HOLD_DETAIL_QUERY_FAILED",
                reason=str(e)
            )

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        col_participant_id: Optional[str] = None
    ) -> int:
        """获取满足条件的总记录数"""
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)
            if col_participant_id:
                conditions.append("col_participant_id = %s")
                params.append(col_participant_id)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取总记录数失败: {e}")
            return 0

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取中央结算系统持股明细统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT trade_date) as trading_days,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(DISTINCT col_participant_id) as participant_count,
                    SUM(col_shareholding) as total_shareholding,
                    AVG(col_shareholding_percent) as avg_shareholding_percent
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    'total_records': row[0] or 0,
                    'trading_days': row[1] or 0,
                    'stock_count': row[2] or 0,
                    'participant_count': row[3] or 0,
                    'total_shareholding': int(row[4]) if row[4] else 0,
                    'avg_shareholding_percent': float(row[5]) if row[5] else 0.0
                }
            return {
                'total_records': 0,
                'trading_days': 0,
                'stock_count': 0,
                'participant_count': 0,
                'total_shareholding': 0,
                'avg_shareholding_percent': 0.0
            }

        except Exception as e:
            logger.error(f"获取中央结算系统持股明细统计信息失败: {e}")
            raise QueryError(
                "获取中央结算系统持股明细统计信息失败",
                error_code="CCASS_HOLD_DETAIL_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期 YYYYMMDD格式，如果无数据返回None

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> latest_date = repo.get_latest_trade_date()
            >>> latest_date = repo.get_latest_trade_date(ts_code='00960.HK')
        """
        try:
            if ts_code:
                query = f"""
                    SELECT MAX(trade_date)
                    FROM {self.TABLE_NAME}
                    WHERE ts_code = %s
                """
                params = (ts_code,)
            else:
                query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
                params = ()

            result = self.execute_query(query, params)
            return result[0][0] if result and result[0][0] else None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新中央结算系统持股明细数据

        Args:
            df: 包含数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = CcassHoldDetailRepository()
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
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('col_participant_id')),
                    to_python_type(row.get('col_participant_name')),
                    to_python_type(row.get('col_shareholding')),
                    to_python_type(row.get('col_shareholding_percent'))
                ))

            # UPSERT 语句
            insert_query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, ts_code, name, col_participant_id, col_participant_name,
                 col_shareholding, col_shareholding_percent, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (trade_date, ts_code, col_participant_id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    col_participant_name = EXCLUDED.col_participant_name,
                    col_shareholding = EXCLUDED.col_shareholding,
                    col_shareholding_percent = EXCLUDED.col_shareholding_percent,
                    updated_at = NOW()
            """

            count = self.execute_batch(insert_query, values)
            logger.info(f"成功插入/更新 {count} 条中央结算系统持股明细数据")
            return count

        except Exception as e:
            logger.error(f"批量插入/更新中央结算系统持股明细数据失败: {e}")
            raise QueryError(
                "批量插入/更新中央结算系统持股明细数据失败",
                error_code="CCASS_HOLD_DETAIL_BULK_UPSERT_FAILED",
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
            >>> repo = CcassHoldDetailRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
            >>> count = repo.delete_by_date_range('20240101', '20240131', ts_code='00960.HK')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)
            query = f"DELETE FROM {self.TABLE_NAME} WHERE {where_clause}"

            count = self.execute_update(query, tuple(params))
            logger.info(f"成功删除 {count} 条中央结算系统持股明细数据")
            return count

        except Exception as e:
            logger.error(f"删除中央结算系统持股明细数据失败: {e}")
            raise QueryError(
                "删除中央结算系统持股明细数据失败",
                error_code="CCASS_HOLD_DETAIL_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            数据是否存在

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> exists = repo.exists_by_date('20240115')
            >>> exists = repo.exists_by_date('20240115', ts_code='00960.HK')
        """
        try:
            if ts_code:
                query = f"""
                    SELECT EXISTS(
                        SELECT 1 FROM {self.TABLE_NAME}
                        WHERE trade_date = %s AND ts_code = %s
                    )
                """
                params = (trade_date, ts_code)
            else:
                query = f"""
                    SELECT EXISTS(
                        SELECT 1 FROM {self.TABLE_NAME}
                        WHERE trade_date = %s
                    )
                """
                params = (trade_date,)

            result = self.execute_query(query, params)
            return result[0][0] if result else False

        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取指定条件的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            记录数

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
            >>> count = repo.get_record_count('20240101', '20240131', ts_code='00960.HK')
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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"

            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0

    def get_top_participants(
        self,
        trade_date: str,
        ts_code: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期的TOP持股机构

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回TOP N

        Returns:
            TOP持股机构列表

        Examples:
            >>> repo = CcassHoldDetailRepository()
            >>> top_participants = repo.get_top_participants('20240115', limit=20)
            >>> top_participants = repo.get_top_participants('20240115', ts_code='00960.HK', limit=10)
        """
        try:
            conditions = ["trade_date = %s"]
            params = [trade_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    col_participant_id,
                    col_participant_name,
                    col_shareholding,
                    col_shareholding_percent
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY col_shareholding DESC
                LIMIT %s
            """
            params.append(limit)

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"获取TOP持股机构失败: {e}")
            raise QueryError(
                "获取TOP持股机构失败",
                error_code="CCASS_HOLD_DETAIL_TOP_PARTICIPANTS_FAILED",
                reason=str(e)
            )

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'name': row[2],
            'col_participant_id': row[3],
            'col_participant_name': row[4],
            'col_shareholding': int(row[5]) if row[5] is not None else None,
            'col_shareholding_percent': float(row[6]) if row[6] is not None else None,
            'created_at': row[7],
            'updated_at': row[8]
        }
