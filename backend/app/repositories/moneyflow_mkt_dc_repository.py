"""
大盘资金流向数据访问层（东方财富DC）

提供东方财富大盘资金流向数据的增删改查操作，支持按日期范围查询、
批量插入、统计分析等功能。

数据表: moneyflow_mkt_dc
数据源: 东方财富大盘资金流向（每日盘后更新）
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class MoneyflowMktDcRepository(BaseRepository):
    """
    大盘资金流向数据访问层

    职责：
    - 按日期范围查询大盘资金流向数据
    - 批量插入/更新资金流向数据
    - 获取主力资金统计信息
    - 查询资金流向趋势
    """

    TABLE_NAME = "moneyflow_mkt_dc"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ MoneyflowMktDcRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询大盘资金流向数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            大盘资金流向数据列表

        Examples:
            >>> repo = MoneyflowMktDcRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    trade_date,
                    close_sh,
                    pct_change_sh,
                    close_sz,
                    pct_change_sz,
                    net_amount,
                    net_amount_rate,
                    buy_elg_amount,
                    buy_elg_amount_rate,
                    buy_lg_amount,
                    buy_lg_amount_rate,
                    buy_md_amount,
                    buy_md_amount_rate,
                    buy_sm_amount,
                    buy_sm_amount_rate,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC
            """

            query += f" LIMIT {self._enforce_limit(limit)}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, tuple(params))

            return [
                {
                    "trade_date": row[0],
                    "close_sh": float(row[1]) if row[1] else 0,
                    "pct_change_sh": float(row[2]) if row[2] else 0,
                    "close_sz": float(row[3]) if row[3] else 0,
                    "pct_change_sz": float(row[4]) if row[4] else 0,
                    "net_amount": float(row[5]) if row[5] else 0,
                    "net_amount_rate": float(row[6]) if row[6] else 0,
                    "buy_elg_amount": float(row[7]) if row[7] else 0,
                    "buy_elg_amount_rate": float(row[8]) if row[8] else 0,
                    "buy_lg_amount": float(row[9]) if row[9] else 0,
                    "buy_lg_amount_rate": float(row[10]) if row[10] else 0,
                    "buy_md_amount": float(row[11]) if row[11] else 0,
                    "buy_md_amount_rate": float(row[12]) if row[12] else 0,
                    "buy_sm_amount": float(row[13]) if row[13] else 0,
                    "buy_sm_amount_rate": float(row[14]) if row[14] else 0,
                    "created_at": row[15].isoformat() if row[15] else None,
                    "updated_at": row[16].isoformat() if row[16] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询大盘资金流向数据失败: {e}")
            raise QueryError(
                "大盘资金流向数据查询失败",
                error_code="MONEYFLOW_MKT_DC_QUERY_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取大盘资金流向统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"主力资金平均净流入: {stats['avg_net_amount']}")
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
                    AVG(net_amount) as avg_net_amount,
                    SUM(net_amount) as total_net_amount,
                    MAX(net_amount) as max_net_amount,
                    MIN(net_amount) as min_net_amount,
                    AVG(buy_elg_amount) as avg_buy_elg_amount,
                    MAX(buy_elg_amount) as max_buy_elg_amount,
                    AVG(buy_lg_amount) as avg_buy_lg_amount,
                    MAX(buy_lg_amount) as max_buy_lg_amount,
                    AVG(pct_change_sh) as avg_pct_change_sh,
                    AVG(pct_change_sz) as avg_pct_change_sz,
                    MAX(trade_date) as latest_date,
                    MIN(trade_date) as earliest_date,
                    COUNT(*) as count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and result[0]:
                row = result[0]
                return {
                    "avg_net_amount": float(row[0]) if row[0] else 0,
                    "total_net_amount": float(row[1]) if row[1] else 0,
                    "max_net_amount": float(row[2]) if row[2] else 0,
                    "min_net_amount": float(row[3]) if row[3] else 0,
                    "avg_buy_elg_amount": float(row[4]) if row[4] else 0,
                    "max_buy_elg_amount": float(row[5]) if row[5] else 0,
                    "avg_buy_lg_amount": float(row[6]) if row[6] else 0,
                    "max_buy_lg_amount": float(row[7]) if row[7] else 0,
                    "avg_pct_change_sh": float(row[8]) if row[8] else 0,
                    "avg_pct_change_sz": float(row[9]) if row[9] else 0,
                    "latest_date": row[10] or "",
                    "earliest_date": row[11] or "",
                    "count": row[12] or 0
                }

            return {
                "avg_net_amount": 0, "total_net_amount": 0,
                "max_net_amount": 0, "min_net_amount": 0,
                "avg_buy_elg_amount": 0, "max_buy_elg_amount": 0,
                "avg_buy_lg_amount": 0, "max_buy_lg_amount": 0,
                "avg_pct_change_sh": 0, "avg_pct_change_sz": 0,
                "latest_date": "", "earliest_date": "", "count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取大盘资金流向统计失败: {e}")
            raise QueryError(
                "大盘资金流向统计查询失败",
                error_code="MONEYFLOW_MKT_DC_STATS_FAILED",
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

    def get_by_trade_date(self, trade_date: str) -> Optional[Dict]:
        """
        获取指定日期的大盘资金流向数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            资金流向数据，如果不存在则返回None
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    close_sh,
                    pct_change_sh,
                    close_sz,
                    pct_change_sz,
                    net_amount,
                    net_amount_rate,
                    buy_elg_amount,
                    buy_lg_amount,
                    buy_md_amount,
                    buy_sm_amount
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
            """

            results = self.execute_query(query, (trade_date,))

            if results:
                row = results[0]
                return {
                    "trade_date": row[0],
                    "close_sh": float(row[1]) if row[1] else 0,
                    "pct_change_sh": float(row[2]) if row[2] else 0,
                    "close_sz": float(row[3]) if row[3] else 0,
                    "pct_change_sz": float(row[4]) if row[4] else 0,
                    "net_amount": float(row[5]) if row[5] else 0,
                    "net_amount_rate": float(row[6]) if row[6] else 0,
                    "buy_elg_amount": float(row[7]) if row[7] else 0,
                    "buy_lg_amount": float(row[8]) if row[8] else 0,
                    "buy_md_amount": float(row[9]) if row[9] else 0,
                    "buy_sm_amount": float(row[10]) if row[10] else 0
                }

            return None

        except PsycopgDatabaseError as e:
            logger.error(f"查询指定日期大盘资金流向数据失败: {e}")
            raise QueryError(
                "大盘资金流向数据查询失败",
                error_code="MONEYFLOW_MKT_DC_QUERY_BY_DATE_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    def get_main_force_trend(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        获取主力资金流向趋势

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            主力资金趋势列表
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    net_amount,
                    buy_elg_amount,
                    buy_lg_amount
                FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
                ORDER BY trade_date ASC
            """

            results = self.execute_query(query, (start_date, end_date))

            return [
                {
                    "trade_date": row[0],
                    "net_amount": float(row[1]) if row[1] else 0,
                    "buy_elg_amount": float(row[2]) if row[2] else 0,
                    "buy_lg_amount": float(row[3]) if row[3] else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"获取主力资金趋势失败: {e}")
            raise QueryError(
                "主力资金趋势查询失败",
                error_code="MAIN_FORCE_TREND_FAILED",
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新大盘资金流向数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 资金流向数据 DataFrame，必须包含 trade_date 等列

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
            required_columns = {'trade_date'}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(
                    f"大盘资金流向 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = [
                'trade_date', 'close_sh', 'pct_change_sh', 'close_sz', 'pct_change_sz',
                'net_amount', 'net_amount_rate',
                'buy_elg_amount', 'buy_elg_amount_rate',
                'buy_lg_amount', 'buy_lg_amount_rate',
                'buy_md_amount', 'buy_md_amount_rate',
                'buy_sm_amount', 'buy_sm_amount_rate'
            ]

            # 确保所有列都存在（缺失的填充为0）
            for col in columns:
                if col not in df.columns:
                    if col != 'trade_date':
                        df[col] = 0

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
                for col in columns if col != 'trade_date'
            ])

            query = f"""
                INSERT INTO {self.TABLE_NAME} ({columns_str}, updated_at)
                VALUES ({placeholders}, NOW())
                ON CONFLICT (trade_date)
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

                logger.info(f"✓ 批量插入/更新大盘资金流向数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入大盘资金流向数据失败: {e}")
            raise DatabaseError(
                "大盘资金流向数据批量插入失败",
                error_code="MONEYFLOW_MKT_DC_BULK_INSERT_FAILED",
                count=len(df),
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
            删除的行数
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """

            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"✓ 删除大盘资金流向数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除大盘资金流向数据失败: {e}")
            raise DatabaseError(
                "大盘资金流向数据删除失败",
                error_code="MONEYFLOW_MKT_DC_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在
        """
        try:
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
