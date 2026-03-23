"""
券商每月荐股 Repository

负责 broker_recommend 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class BrokerRecommendRepository(BaseRepository):
    """券商每月荐股数据仓库"""

    TABLE_NAME = "broker_recommend"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ BrokerRecommendRepository initialized")

    def get_by_month_range(
        self,
        start_month: str,
        end_month: str,
        broker: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按月度范围查询数据

        Args:
            start_month: 开始月度,格式：YYYYMM
            end_month: 结束月度,格式：YYYYMM
            broker: 券商名称（可选）
            ts_code: 股票代码（可选）
            limit: 限制返回数量

        Returns:
            数据列表

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> data = repo.get_by_month_range('202101', '202112')
        """
        try:
            query = f"""
                SELECT month, broker, ts_code, name,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE month >= %s AND month <= %s
            """
            params = [start_month, end_month]

            if broker:
                query += " AND broker = %s"
                params.append(broker)

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            query += " ORDER BY month DESC, broker, ts_code"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询券商荐股数据失败: {e}")
            raise

    def get_by_month(
        self,
        month: str,
        broker: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按单个月度查询数据

        Args:
            month: 月度,格式：YYYYMM
            broker: 券商名称（可选）
            limit: 限制返回数量

        Returns:
            数据列表

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> data = repo.get_by_month('202106')
        """
        try:
            query = f"""
                SELECT month, broker, ts_code, name,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE month = %s
            """
            params = [month]

            if broker:
                query += " AND broker = %s"
                params.append(broker)

            query += " ORDER BY broker, ts_code"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询券商荐股数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_month: 开始月度（可选）
            end_month: 结束月度（可选）

        Returns:
            统计数据字典

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> stats = repo.get_statistics('202101', '202112')
        """
        try:
            query = f"""
                SELECT
                    COUNT(DISTINCT month) as month_count,
                    COUNT(DISTINCT broker) as broker_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(*) as total_records
                FROM {self.TABLE_NAME}
            """
            params = []

            if start_month and end_month:
                query += " WHERE month >= %s AND month <= %s"
                params = [start_month, end_month]
            elif start_month:
                query += " WHERE month >= %s"
                params = [start_month]
            elif end_month:
                query += " WHERE month <= %s"
                params = [end_month]

            result = self.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    "month_count": row[0] or 0,
                    "broker_count": row[1] or 0,
                    "stock_count": row[2] or 0,
                    "total_records": row[3] or 0
                }
            return {
                "month_count": 0,
                "broker_count": 0,
                "stock_count": 0,
                "total_records": 0
            }

        except Exception as e:
            logger.error(f"获取券商荐股统计失败: {e}")
            raise

    def get_latest_month(self) -> Optional[str]:
        """
        获取最新月度

        Returns:
            最新月度字符串(YYYYMM)

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> latest = repo.get_latest_month()
        """
        try:
            query = f"""
                SELECT month
                FROM {self.TABLE_NAME}
                ORDER BY month DESC
                LIMIT 1
            """
            result = self.execute_query(query)
            return result[0][0] if result else None

        except Exception as e:
            logger.error(f"获取最新月度失败: {e}")
            raise

    def get_broker_list(self, month: Optional[str] = None) -> List[str]:
        """
        获取券商列表

        Args:
            month: 月度（可选）

        Returns:
            券商名称列表

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> brokers = repo.get_broker_list('202106')
        """
        try:
            query = f"""
                SELECT DISTINCT broker
                FROM {self.TABLE_NAME}
            """
            params = []

            if month:
                query += " WHERE month = %s"
                params.append(month)

            query += " ORDER BY broker"

            result = self.execute_query(query, tuple(params))
            return [row[0] for row in result]

        except Exception as e:
            logger.error(f"获取券商列表失败: {e}")
            raise

    def get_top_stocks(
        self,
        month: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取某月份被推荐次数最多的股票

        Args:
            month: 月度,格式：YYYYMM
            limit: 返回数量

        Returns:
            股票列表（按推荐次数降序）

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> top_stocks = repo.get_top_stocks('202106', 10)
        """
        try:
            query = f"""
                SELECT
                    ts_code,
                    name,
                    COUNT(*) as recommend_count
                FROM {self.TABLE_NAME}
                WHERE month = %s
                GROUP BY ts_code, name
                ORDER BY recommend_count DESC
                LIMIT %s
            """
            result = self.execute_query(query, (month, limit))
            return [
                {
                    "ts_code": row[0],
                    "name": row[1],
                    "recommend_count": row[2]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"获取热门股票失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新数据

        Args:
            df: 包含券商荐股数据的DataFrame

        Returns:
            影响的行数

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空,跳过插入")
            return 0

        try:
            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    self._to_python_type(row.get('month')),
                    self._to_python_type(row.get('broker')),
                    self._to_python_type(row.get('ts_code')),
                    self._to_python_type(row.get('name'))
                ))

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (month, broker, ts_code, name)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (month, broker, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = CURRENT_TIMESTAMP
            """

            count = self.execute_batch(query, values)
            logger.info(f"批量插入/更新券商荐股数据: {count} 条")
            return count

        except Exception as e:
            logger.error(f"批量插入券商荐股数据失败: {e}")
            raise

    def delete_by_month(self, month: str) -> int:
        """
        删除指定月度的数据

        Args:
            month: 月度,格式：YYYYMM

        Returns:
            删除的行数

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> count = repo.delete_by_month('202106')
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE month = %s"
            count = self.execute_update(query, (month,))
            logger.info(f"删除券商荐股数据: {count} 条")
            return count

        except Exception as e:
            logger.error(f"删除券商荐股数据失败: {e}")
            raise

    def exists_by_month(self, month: str) -> bool:
        """
        检查指定月度是否存在数据

        Args:
            month: 月度,格式：YYYYMM

        Returns:
            是否存在

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> exists = repo.exists_by_month('202106')
        """
        try:
            query = f"SELECT 1 FROM {self.TABLE_NAME} WHERE month = %s LIMIT 1"
            result = self.execute_query(query, (month,))
            return len(result) > 0

        except Exception as e:
            logger.error(f"检查券商荐股数据是否存在失败: {e}")
            raise

    def get_record_count(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> int:
        """
        获取记录数量

        Args:
            start_month: 开始月度（可选）
            end_month: 结束月度（可选）

        Returns:
            记录数量

        Examples:
            >>> repo = BrokerRecommendRepository()
            >>> count = repo.get_record_count('202101', '202112')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME}"
            params = []

            if start_month and end_month:
                query += " WHERE month >= %s AND month <= %s"
                params = [start_month, end_month]
            elif start_month:
                query += " WHERE month >= %s"
                params = [start_month]
            elif end_month:
                query += " WHERE month <= %s"
                params = [end_month]

            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取券商荐股记录数失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'month': row[0],
            'broker': row[1],
            'ts_code': row[2],
            'name': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'updated_at': row[5].isoformat() if row[5] else None
        }
