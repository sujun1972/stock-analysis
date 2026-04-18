"""
个股资金流向数据访问层

提供资金流向数据的增删改查操作，支持按日期范围、股票代码查询，
以及批量插入、统计分析等功能。

数据表: moneyflow
数据源: Tushare pro.moneyflow()
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class MoneyflowRepository(BaseRepository):
    """
    个股资金流向数据访问层

    职责：
    - 按日期范围和股票代码查询资金流向数据
    - 批量插入/更新资金流向数据
    - 获取资金流向统计信息
    - 查询资金净流入排名
    """

    TABLE_NAME = "moneyflow"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ MoneyflowRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询资金流向数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            资金流向数据列表

        Examples:
            >>> repo = MoneyflowRepository()
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

            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    buy_sm_vol, buy_sm_amount,
                    sell_sm_vol, sell_sm_amount,
                    buy_md_vol, buy_md_amount,
                    sell_md_vol, sell_md_amount,
                    buy_lg_vol, buy_lg_amount,
                    sell_lg_vol, sell_lg_amount,
                    buy_elg_vol, buy_elg_amount,
                    sell_elg_vol, sell_elg_amount,
                    net_mf_vol, net_mf_amount,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, net_mf_amount DESC
            """

            effective_limit = self._enforce_limit(limit)
            query += f" LIMIT {effective_limit}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, tuple(params))

            return [
                {
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "buy_sm_vol": int(row[2]) if row[2] else 0,
                    "buy_sm_amount": float(row[3]) if row[3] else 0,
                    "sell_sm_vol": int(row[4]) if row[4] else 0,
                    "sell_sm_amount": float(row[5]) if row[5] else 0,
                    "buy_md_vol": int(row[6]) if row[6] else 0,
                    "buy_md_amount": float(row[7]) if row[7] else 0,
                    "sell_md_vol": int(row[8]) if row[8] else 0,
                    "sell_md_amount": float(row[9]) if row[9] else 0,
                    "buy_lg_vol": int(row[10]) if row[10] else 0,
                    "buy_lg_amount": float(row[11]) if row[11] else 0,
                    "sell_lg_vol": int(row[12]) if row[12] else 0,
                    "sell_lg_amount": float(row[13]) if row[13] else 0,
                    "buy_elg_vol": int(row[14]) if row[14] else 0,
                    "buy_elg_amount": float(row[15]) if row[15] else 0,
                    "sell_elg_vol": int(row[16]) if row[16] else 0,
                    "sell_elg_amount": float(row[17]) if row[17] else 0,
                    "net_mf_vol": int(row[18]) if row[18] else 0,
                    "net_mf_amount": float(row[19]) if row[19] else 0,
                    "created_at": row[20].isoformat() if row[20] else None,
                    "updated_at": row[21].isoformat() if row[21] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询资金流向数据失败: {e}")
            raise QueryError(
                "资金流向数据查询失败",
                error_code="MONEYFLOW_QUERY_FAILED",
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
        获取资金流向统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"平均净流入: {stats['avg_net']}")
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
                    AVG(net_mf_amount) as avg_net,
                    MAX(net_mf_amount) as max_net,
                    MIN(net_mf_amount) as min_net,
                    SUM(net_mf_amount) as total_net,
                    AVG(buy_elg_amount) as avg_elg,
                    MAX(buy_elg_amount) as max_elg,
                    AVG(buy_lg_amount) as avg_lg,
                    MAX(buy_lg_amount) as max_lg,
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
                    "avg_net": float(row[0]) if row[0] else 0,
                    "max_net": float(row[1]) if row[1] else 0,
                    "min_net": float(row[2]) if row[2] else 0,
                    "total_net": float(row[3]) if row[3] else 0,
                    "avg_elg": float(row[4]) if row[4] else 0,
                    "max_elg": float(row[5]) if row[5] else 0,
                    "avg_lg": float(row[6]) if row[6] else 0,
                    "max_lg": float(row[7]) if row[7] else 0,
                    "latest_date": row[8] or "",
                    "earliest_date": row[9] or "",
                    "count": row[10] or 0,
                    "stock_count": row[11] or 0
                }

            return {
                "avg_net": 0, "max_net": 0, "min_net": 0, "total_net": 0,
                "avg_elg": 0, "max_elg": 0, "avg_lg": 0, "max_lg": 0,
                "latest_date": "", "earliest_date": "", "count": 0, "stock_count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取资金流向统计失败: {e}")
            raise QueryError(
                "资金流向统计查询失败",
                error_code="MONEYFLOW_STATS_FAILED",
                reason=str(e)
            )

    def get_top_by_net_amount(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期资金净流入排名前N的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数

        Returns:
            排名前N的股票列表

        Examples:
            >>> top_stocks = repo.get_top_by_net_amount('20240115', limit=10)
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ts_code,
                    net_mf_amount,
                    net_mf_vol,
                    buy_elg_amount,
                    buy_lg_amount,
                    buy_md_amount,
                    buy_sm_amount
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY net_mf_amount DESC
                LIMIT %s
            """

            results = self.execute_query(query, (trade_date, limit))

            return [
                {
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "net_mf_amount": float(row[2]) if row[2] else 0,
                    "net_mf_vol": int(row[3]) if row[3] else 0,
                    "buy_elg_amount": float(row[4]) if row[4] else 0,
                    "buy_lg_amount": float(row[5]) if row[5] else 0,
                    "buy_md_amount": float(row[6]) if row[6] else 0,
                    "buy_sm_amount": float(row[7]) if row[7] else 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"获取资金流入排名失败: {e}")
            raise QueryError(
                "资金流入排名查询失败",
                error_code="MONEYFLOW_TOP_FAILED",
                trade_date=trade_date,
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
        批量插入/更新资金流向数据

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
                    f"资金流向 DataFrame 缺少必需列: {', '.join(missing)}"
                )

            # 构建插入语句
            columns = [
                'trade_date', 'ts_code',
                'buy_sm_vol', 'buy_sm_amount', 'sell_sm_vol', 'sell_sm_amount',
                'buy_md_vol', 'buy_md_amount', 'sell_md_vol', 'sell_md_amount',
                'buy_lg_vol', 'buy_lg_amount', 'sell_lg_vol', 'sell_lg_amount',
                'buy_elg_vol', 'buy_elg_amount', 'sell_elg_vol', 'sell_elg_amount',
                'net_mf_vol', 'net_mf_amount'
            ]

            # 确保所有列都存在（缺失的填充为0）
            for col in columns:
                if col not in df.columns:
                    df[col] = 0

            # 标准化 trade_date：Tushare 历史数据有时返回 YYYY-MM-DD（10位），需转为 YYYYMMDD（8位）
            if 'trade_date' in df.columns:
                df['trade_date'] = df['trade_date'].astype(str).str.replace('-', '', regex=False).str[:8]

            # vol 列为 BIGINT，必须转为 Python int；amount 列为 DECIMAL，转为 float
            VOL_COLS = {
                'buy_sm_vol', 'sell_sm_vol', 'buy_md_vol', 'sell_md_vol',
                'buy_lg_vol', 'sell_lg_vol', 'buy_elg_vol', 'sell_elg_vol',
                'net_mf_vol'
            }

            def _to_val(col, v):
                if pd.isna(v):
                    return None
                if col in ('trade_date', 'ts_code'):
                    return str(v)
                if col in VOL_COLS:
                    try:
                        iv = int(float(v))
                        # bigint 范围检查
                        if iv > 9223372036854775807 or iv < -9223372036854775808:
                            return None
                        return iv
                    except (ValueError, OverflowError):
                        return None
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return None

            # 准备数据
            values = []
            for _, row in df.iterrows():
                values.append(tuple(_to_val(col, row[col]) for col in columns))

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

            # 批量执行（使用 executemany，单行出错时跳过并继续）
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                affected_rows = 0
                skip_count = 0
                for value_tuple in values:
                    try:
                        cursor.execute(query, value_tuple)
                        affected_rows += cursor.rowcount
                    except Exception as row_err:
                        conn.rollback()
                        skip_count += 1
                        logger.debug(f"跳过异常行: {row_err} | 值: {value_tuple[:2]}")
                conn.commit()
                cursor.close()

                if skip_count:
                    logger.warning(f"批量插入资金流向：跳过 {skip_count} 条异常行")
                logger.info(f"✓ 批量插入/更新资金流向数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入资金流向数据失败: {e}")
            raise DatabaseError(
                "资金流向数据批量插入失败",
                error_code="MONEYFLOW_BULK_INSERT_FAILED",
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
        删除指定日期范围的资金流向数据

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
            logger.info(f"✓ 删除资金流向数��: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除资金流向数据失败: {e}")
            raise DatabaseError(
                "资金流向数据删除失败",
                error_code="MONEYFLOW_DELETE_FAILED",
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
