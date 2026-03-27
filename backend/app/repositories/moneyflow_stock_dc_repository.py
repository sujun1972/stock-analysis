"""
个股资金流向数据访问层（东方财富DC）

提供东方财富个股资金流向数据的增删改查操作，支持按日期范围、股票代码查询、
批量插入、统计分析等功能。

数据表: moneyflow_stock_dc
数据源: 东方财富个股资金流向（每天盘后更新）
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


# 允许排序的字段白名单（与 Service 层保持一致，双重防护 SQL 注入）
_SORTABLE_COLUMNS = frozenset({'net_amount', 'pct_change', 'buy_elg_amount', 'buy_lg_amount',
                                'buy_md_amount', 'buy_sm_amount', 'close'})


class MoneyflowStockDcRepository(BaseRepository):
    """
    个股资金流向数据访问层（DC版）

    职责：
    - 按日期范围和股票代码查询个股资金流向数据
    - 批量插入/更新资金流向数据
    - 获取个股资金统计信息
    - 查询个股资金流向排名
    """

    TABLE_NAME = "moneyflow_stock_dc"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ MoneyflowStockDcRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> List[Dict]:
        """
        按日期范围查询个股资金流向数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            个股资金流向数据列表

        Examples:
            >>> repo = MoneyflowStockDcRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        try:
            conditions = ["trade_date >= %s", "trade_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            # 排序：Service 层已做白名单校验，Repository 层二次防护
            if sort_by and sort_by in _SORTABLE_COLUMNS:
                order_dir = 'ASC' if sort_order == 'asc' else 'DESC'
                order_clause = f"ORDER BY {sort_by} {order_dir} NULLS LAST"
            else:
                order_clause = "ORDER BY trade_date DESC, net_amount DESC NULLS LAST"

            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    pct_change,
                    close,
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
                {order_clause}
            """

            if limit:
                query += f" LIMIT {int(limit)}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, tuple(params))

            return [
                {
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "name": row[2],
                    "pct_change": float(row[3]) if row[3] else 0,
                    "close": float(row[4]) if row[4] else 0,
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
            logger.error(f"查询个股资金流向数据失败: {e}")
            raise QueryError(
                "个股资金流向数据查询失败",
                error_code="MONEYFLOW_STOCK_DC_QUERY_FAILED",
                start_date=start_date,
                end_date=end_date,
                ts_code=ts_code,
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取个股资金流向统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

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
                    MAX(trade_date) as latest_date,
                    MIN(trade_date) as earliest_date,
                    COUNT(*) as count,
                    COUNT(DISTINCT ts_code) as stock_count
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
                    "latest_date": row[8] or "",
                    "earliest_date": row[9] or "",
                    "count": row[10] or 0,
                    "stock_count": row[11] or 0
                }

            return {
                "avg_net_amount": 0, "total_net_amount": 0,
                "max_net_amount": 0, "min_net_amount": 0,
                "avg_buy_elg_amount": 0, "max_buy_elg_amount": 0,
                "avg_buy_lg_amount": 0, "max_buy_lg_amount": 0,
                "latest_date": "", "earliest_date": "",
                "count": 0, "stock_count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取个股资金流向统计失败: {e}")
            raise QueryError(
                "个股资金流向统计查询失败",
                error_code="MONEYFLOW_STOCK_DC_STATS_FAILED",
                reason=str(e)
            )

    def get_top_by_net_amount(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期主力资金净流入排名前N的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数

        Returns:
            排名前N的股票列表

        Examples:
            >>> top_stocks = repo.get_top_by_net_amount('20240115', limit=20)
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    name,
                    pct_change,
                    close,
                    net_amount,
                    buy_elg_amount,
                    buy_lg_amount
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY net_amount DESC
                LIMIT %s
            """

            results = self.execute_query(query, (trade_date, limit))

            return [
                {
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "name": row[2],
                    "pct_change": float(row[3]) if row[3] else 0,
                    "close": float(row[4]) if row[4] else 0,
                    "net_amount": float(row[5]) if row[5] else 0,
                    "buy_elg_amount": float(row[6]) if row[6] else 0,
                    "buy_lg_amount": float(row[7]) if row[7] else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"获取资金流入排名失败: {e}")
            raise QueryError(
                "资金流入排名查询失败",
                error_code="MONEYFLOW_STOCK_DC_TOP_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期（格式：YYYYMMDD），如果没有数据则返回None
        """
        try:
            if ts_code:
                query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME} WHERE ts_code = %s"
                result = self.execute_query(query, (ts_code,))
            else:
                query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
                result = self.execute_query(query)

            return result[0][0] if result and result[0][0] else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新个股资金流向数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 资金流向数据 DataFrame，必须包含 trade_date, ts_code 等列

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
                    f"个股资金流向 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = [
                'trade_date', 'ts_code', 'name',
                'pct_change', 'close',
                'net_amount', 'net_amount_rate',
                'buy_elg_amount', 'buy_elg_amount_rate',
                'buy_lg_amount', 'buy_lg_amount_rate',
                'buy_md_amount', 'buy_md_amount_rate',
                'buy_sm_amount', 'buy_sm_amount_rate'
            ]

            # 确保所有列都存在（缺失的填充为默认值）
            for col in columns:
                if col not in df.columns:
                    if col == 'name':
                        df[col] = None
                    elif col not in ['trade_date', 'ts_code']:
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

                logger.info(f"✓ 批量插入/更新个股资金流向数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入个股资金流向数据失败: {e}")
            raise DatabaseError(
                "个股资金流向数据批量插入失败",
                error_code="MONEYFLOW_STOCK_DC_BULK_INSERT_FAILED",
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
        删除指定日期范围的数据

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
            logger.info(f"✓ 删除个股资金流向数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除个股资金流向数据失败: {e}")
            raise DatabaseError(
                "个股资金流向数据删除失败",
                error_code="MONEYFLOW_STOCK_DC_DELETE_FAILED",
                start_date=start_date,
                end_date=end_date,
                reason=str(e)
            )

    # ==================== 数据验证 ====================

    def exists_by_date(
        self,
        trade_date: str,
        ts_code: Optional[str] = None
    ) -> bool:
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
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else None

            return self.count(
                self.TABLE_NAME,
                where_clause,
                tuple(params) if params else None
            )
        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0

    def get_stock_list(self, trade_date: Optional[str] = None) -> List[str]:
        """
        获取有资金流向数据的股票代码列表

        Args:
            trade_date: 交易日期（可选，不指定则返回所有股票）

        Returns:
            股票代码列表
        """
        try:
            if trade_date:
                query = f"""
                    SELECT DISTINCT ts_code
                    FROM {self.TABLE_NAME}
                    WHERE trade_date = %s
                    ORDER BY ts_code
                """
                results = self.execute_query(query, (trade_date,))
            else:
                query = f"""
                    SELECT DISTINCT ts_code
                    FROM {self.TABLE_NAME}
                    ORDER BY ts_code
                """
                results = self.execute_query(query)

            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return []
