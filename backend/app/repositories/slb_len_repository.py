"""
转融资交易汇总数据访问层

提供转融通融资汇总数据的增删改查操作，支持按日期范围查询，
以及批量插入、统计分析等功能。

数据表: slb_len
数据源: Tushare slb_len 接口
积分消耗: 2000积分/分钟200次，5000积分500次
单次限量: 最大5000行
"""

from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class SlbLenRepository(BaseRepository):
    """
    转融资交易汇总数据访问层

    职责：
    - 按日期范围查询转融资汇总数据
    - 批量插入/更新转融资数据
    - 获取转融资统计信息
    - 数据存在性检查
    """

    TABLE_NAME = "slb_len"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ SlbLenRepository initialized")

    # ==================== 查询操作 ====================

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询转融资交易汇总数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 返回记录数（可选）
            offset: 偏移量

        Returns:
            转融资数据列表

        Examples:
            >>> repo = SlbLenRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ob,
                    auc_amount,
                    repo_amount,
                    repay_amount,
                    cb,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
                ORDER BY trade_date DESC
            """

            if limit:
                query += f" LIMIT {int(limit)}"
            if offset > 0:
                query += f" OFFSET {int(offset)}"

            results = self.execute_query(query, (start_date, end_date))

            return [
                {
                    "trade_date": row[0],
                    "ob": float(row[1]) if row[1] else 0,
                    "auc_amount": float(row[2]) if row[2] else 0,
                    "repo_amount": float(row[3]) if row[3] else 0,
                    "repay_amount": float(row[4]) if row[4] else 0,
                    "cb": float(row[5]) if row[5] else 0,
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询转融资数据失败: {e}")
            raise QueryError(
                "转融资数据查询失败",
                error_code="SLB_LEN_QUERY_FAILED",
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
        获取转融资统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计数据字典

        Examples:
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(f"平均期末余额: {stats['avg_cb']}")
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
                    AVG(cb) as avg_cb,
                    MAX(cb) as max_cb,
                    MIN(cb) as min_cb,
                    AVG(ob) as avg_ob,
                    SUM(auc_amount) as total_auc_amount,
                    SUM(repo_amount) as total_repo_amount,
                    SUM(repay_amount) as total_repay_amount,
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
                    "avg_cb": float(row[0]) if row[0] else 0,
                    "max_cb": float(row[1]) if row[1] else 0,
                    "min_cb": float(row[2]) if row[2] else 0,
                    "avg_ob": float(row[3]) if row[3] else 0,
                    "total_auc_amount": float(row[4]) if row[4] else 0,
                    "total_repo_amount": float(row[5]) if row[5] else 0,
                    "total_repay_amount": float(row[6]) if row[6] else 0,
                    "latest_date": row[7] or "",
                    "earliest_date": row[8] or "",
                    "count": row[9] or 0
                }

            return {
                "avg_cb": 0, "max_cb": 0, "min_cb": 0, "avg_ob": 0,
                "total_auc_amount": 0, "total_repo_amount": 0,
                "total_repay_amount": 0,
                "latest_date": "", "earliest_date": "", "count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取转融资统计失败: {e}")
            raise QueryError(
                "转融资统计查询失败",
                error_code="SLB_LEN_STATS_FAILED",
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
        获取指定日期的转融资数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            该日期的数据，如果不存在则返回None
        """
        try:
            query = f"""
                SELECT
                    trade_date,
                    ob,
                    auc_amount,
                    repo_amount,
                    repay_amount,
                    cb
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
            """

            results = self.execute_query(query, (trade_date,))

            if results and results[0]:
                row = results[0]
                return {
                    "trade_date": row[0],
                    "ob": float(row[1]) if row[1] else 0,
                    "auc_amount": float(row[2]) if row[2] else 0,
                    "repo_amount": float(row[3]) if row[3] else 0,
                    "repay_amount": float(row[4]) if row[4] else 0,
                    "cb": float(row[5]) if row[5] else 0
                }

            return None

        except PsycopgDatabaseError as e:
            logger.error(f"查询指定日期转融资数据失败: {e}")
            raise QueryError(
                "转融资数据查询失败",
                error_code="SLB_LEN_QUERY_BY_DATE_FAILED",
                trade_date=trade_date,
                reason=str(e)
            )

    # ==================== 写入操作 ====================

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新转融资数据

        使用 ON CONFLICT DO UPDATE 实现 upsert 语义。

        Args:
            df: 转融资数据 DataFrame，必须包含 trade_date 等列

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
            if 'trade_date' not in df.columns:
                raise ValueError("转融资 DataFrame 缺少必需列: trade_date")

            # 构建插入语句
            columns = [
                'trade_date', 'ob', 'auc_amount',
                'repo_amount', 'repay_amount', 'cb'
            ]

            # 确保所有列都存在（缺失的填充为None）
            for col in columns:
                if col not in df.columns:
                    if col != 'trade_date':
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

                logger.info(f"✓ 批量插入/更新转融资数据: {affected_rows} 条")
                return affected_rows

            finally:
                self.db.release_connection(conn)

        except ValueError:
            raise
        except PsycopgDatabaseError as e:
            logger.error(f"批量插入转融资数据失败: {e}")
            raise DatabaseError(
                "转融资数据批量插入失败",
                error_code="SLB_LEN_BULK_INSERT_FAILED",
                count=len(df),
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        删除指定日期范围的转融资数据

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
            logger.info(f"✓ 删除转融资数据: {count} 条")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"删除转融资数据失败: {e}")
            raise DatabaseError(
                "转融资数据删除失败",
                error_code="SLB_LEN_DELETE_FAILED",
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
