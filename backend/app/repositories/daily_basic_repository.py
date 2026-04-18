"""
每日指标数据访问层

提供每日指标数据的增删改查操作，支持按日期范围、股票代码查询，
以及批量插入、统计分析等功能。

数据表: daily_basic
数据源: Tushare pro.daily_basic()
"""

from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class DailyBasicRepository(BaseRepository):
    """
    每日指标数据访问层

    职责：
    - 按日期范围和股票代码查询每日指标数据
    - 批量插入/更新每日指标数据
    - 获取每日指标统计信息
    - 查询最新交易日期
    """

    TABLE_NAME = "daily_basic"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ DailyBasicRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_code_and_date_range(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询每日指标数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数

        Returns:
            每日指标数据列表

        Examples:
            >>> repo = DailyBasicRepository()
            >>> data = repo.get_by_code_and_date_range('000001.SZ')
            >>> data = repo.get_by_code_and_date_range('000001.SZ', '20240101', '20240131')
        """
        try:
            conditions = ["ts_code = %s"]
            params = [ts_code]

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code, trade_date, close, turnover_rate, turnover_rate_f,
                    volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm,
                    total_share, float_share, free_share, total_mv, circ_mv,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC
                LIMIT %s
            """

            params.append(limit)
            results = self.execute_query(query, tuple(params))

            return [
                {
                    "ts_code": row[0],
                    "trade_date": row[1].strftime('%Y%m%d') if hasattr(row[1], 'strftime') else row[1],
                    "close": float(row[2]) if row[2] is not None else None,
                    "turnover_rate": float(row[3]) if row[3] is not None else None,
                    "turnover_rate_f": float(row[4]) if row[4] is not None else None,
                    "volume_ratio": float(row[5]) if row[5] is not None else None,
                    "pe": float(row[6]) if row[6] is not None else None,
                    "pe_ttm": float(row[7]) if row[7] is not None else None,
                    "pb": float(row[8]) if row[8] is not None else None,
                    "ps": float(row[9]) if row[9] is not None else None,
                    "ps_ttm": float(row[10]) if row[10] is not None else None,
                    "dv_ratio": float(row[11]) if row[11] is not None else None,
                    "dv_ttm": float(row[12]) if row[12] is not None else None,
                    "total_share": float(row[13]) if row[13] is not None else None,
                    "float_share": float(row[14]) if row[14] is not None else None,
                    "free_share": float(row[15]) if row[15] is not None else None,
                    "total_mv": float(row[16]) if row[16] is not None else None,
                    "circ_mv": float(row[17]) if row[17] is not None else None,
                    "created_at": row[18].isoformat() if row[18] else None,
                    "updated_at": row[19].isoformat() if row[19] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询每日指标数据失败: {e}")
            raise QueryError(
                "每日指标数据查询失败",
                error_code="DAILY_BASIC_QUERY_FAILED",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询每日指标数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            每日指标数据列表

        Examples:
            >>> repo = DailyBasicRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code, trade_date, close, turnover_rate, turnover_rate_f,
                    volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm,
                    total_share, float_share, free_share, total_mv, circ_mv,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
            """

            effective_limit = self._enforce_limit(limit)
            query += f" LIMIT {effective_limit}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, tuple(params))

            return [
                {
                    "ts_code": row[0],
                    "trade_date": row[1].strftime('%Y%m%d') if hasattr(row[1], 'strftime') else row[1],
                    "close": float(row[2]) if row[2] is not None else None,
                    "turnover_rate": float(row[3]) if row[3] is not None else None,
                    "turnover_rate_f": float(row[4]) if row[4] is not None else None,
                    "volume_ratio": float(row[5]) if row[5] is not None else None,
                    "pe": float(row[6]) if row[6] is not None else None,
                    "pe_ttm": float(row[7]) if row[7] is not None else None,
                    "pb": float(row[8]) if row[8] is not None else None,
                    "ps": float(row[9]) if row[9] is not None else None,
                    "ps_ttm": float(row[10]) if row[10] is not None else None,
                    "dv_ratio": float(row[11]) if row[11] is not None else None,
                    "dv_ttm": float(row[12]) if row[12] is not None else None,
                    "total_share": float(row[13]) if row[13] is not None else None,
                    "float_share": float(row[14]) if row[14] is not None else None,
                    "free_share": float(row[15]) if row[15] is not None else None,
                    "total_mv": float(row[16]) if row[16] is not None else None,
                    "circ_mv": float(row[17]) if row[17] is not None else None,
                    "created_at": row[18].isoformat() if row[18] else None,
                    "updated_at": row[19].isoformat() if row[19] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询每日指标数据失败: {e}")
            raise QueryError(
                "每日指标数据查询失败",
                error_code="DAILY_BASIC_QUERY_FAILED",
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取每日指标统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"股票数量: {stats['stock_count']}")
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
                SELECT
                    COUNT(DISTINCT ts_code) as stock_count,
                    MIN(trade_date) as earliest_date,
                    MAX(trade_date) as latest_date,
                    COUNT(*) as total_records,
                    AVG(turnover_rate) as avg_turnover_rate,
                    AVG(pe_ttm) as avg_pe_ttm
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and result[0]:
                row = result[0]
                # 转换日期格式
                earliest_date = row[1]
                latest_date = row[2]
                if hasattr(earliest_date, 'strftime'):
                    earliest_date = earliest_date.strftime('%Y%m%d')
                if hasattr(latest_date, 'strftime'):
                    latest_date = latest_date.strftime('%Y%m%d')

                # 处理平均值（可能是NaN）
                import math
                avg_turnover = float(row[4]) if row[4] is not None else 0.0
                avg_pe = float(row[5]) if row[5] is not None else 0.0

                # NaN检查
                if math.isnan(avg_turnover):
                    avg_turnover = 0.0
                if math.isnan(avg_pe):
                    avg_pe = 0.0

                return {
                    "stock_count": row[0] or 0,
                    "date_range": {
                        "earliest_date": earliest_date or "",
                        "latest_date": latest_date or ""
                    },
                    "total_records": row[3] or 0,
                    "avg_turnover_rate": avg_turnover,
                    "avg_pe_ttm": avg_pe
                }

            return {
                "stock_count": 0,
                "date_range": {
                    "earliest_date": "",
                    "latest_date": ""
                },
                "total_records": 0,
                "avg_turnover_rate": 0.0,
                "avg_pe_ttm": 0.0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取每日指标统计失败: {e}")
            raise QueryError(
                "每日指标统计查询失败",
                error_code="DAILY_BASIC_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（格式：YYYYMMDD），如果没有数据则返回None
        """
        try:
            query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
            result = self.execute_query(query)
            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新每日指标数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 每日指标数据 DataFrame，必须包含 trade_date, ts_code 等列

        Returns:
            影响的行数

        Raises:
            ValueError: DataFrame格式不正确
            DatabaseError: 数据库操作失败

        Examples:
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
            >>> print(f"插入/更新了 {count} 条记录")
        """
        if df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 验证必需列
            required_columns = {'trade_date', 'ts_code'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"每日指标 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = [
                'trade_date', 'ts_code', 'close', 'turnover_rate', 'turnover_rate_f',
                'volume_ratio', 'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm', 'dv_ratio', 'dv_ttm',
                'total_share', 'float_share', 'free_share', 'total_mv', 'circ_mv'
            ]

            # 确保所有列都存在（缺失的填充为NULL）
            for col in columns:
                if col not in df.columns:
                    df[col] = None

            # 准备数据
            values = []
            for _, row in df.iterrows():
                values.append(tuple(row[col] for col in columns))

            if not values:
                return 0

            # 构建SQL
            placeholders = ','.join(['%s'] * len(columns))
            columns_str = ','.join(columns)
            update_columns = ','.join([
                f"{col} = EXCLUDED.{col}"
                for col in columns if col not in ['trade_date', 'ts_code']
            ])

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    {update_columns},
                    updated_at = NOW()
            """

            # 批量执行
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                affected_rows = 0
                for value_tuple in values:
                    cursor.execute(query, value_tuple)
                    affected_rows += cursor.rowcount
                conn.commit()
                cursor.close()

                logger.info(f"✓ 批量插入/更新每日指标数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入每日指标数据失败: {e}")
            raise DatabaseError(
                "每日指标数据批量插入失败",
                error_code="DAILY_BASIC_BULK_INSERT_FAILED",
                count=len(df),
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围的每日指标数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选，不指定则删除所有股票）

        Returns:
            删除的行数
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
            logger.info(f"✓ 删除���日指标数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除每日指标数据失败: {e}")
            raise DatabaseError(
                "每日指标数据删除失败",
                error_code="DAILY_BASIC_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            是否存在
        """
        try:
            if ts_code:
                return self.exists(
                    self.TABLE_NAME,
                    "trade_date = %s AND ts_code = %s",
                    (trade_date, ts_code)
                )
            else:
                return self.exists(
                    self.TABLE_NAME,
                    "trade_date = %s",
                    (trade_date,)
                )
        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            记录数
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

            where_clause = " AND ".join(conditions) if conditions else None

            return self.count(
                self.TABLE_NAME,
                where_clause,
                tuple(params) if params else None
            )
        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0
