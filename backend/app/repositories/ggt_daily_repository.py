"""
港股通每日成交统计 Repository

职责：
- 管理 ggt_daily 表的数据访问
- 提供查询、统计、插入/更新功能
"""

import pandas as pd
from typing import List, Dict, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository


class GgtDailyRepository(BaseRepository):
    """港股通每日成交统计数据访问层"""

    TABLE_NAME = "ggt_daily"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ GgtDailyRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询港股通成交数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选，默认'19900101'）
            end_date: 结束日期，格式：YYYYMMDD（可选，默认'29991231'）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = GgtDailyRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131', 30)
        """
        try:
            # 默认值
            start_date = start_date or '19900101'
            end_date = end_date or '29991231'

            query = f"""
                SELECT trade_date, buy_amount, buy_volume, sell_amount, sell_volume,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
                ORDER BY trade_date DESC
            """

            extra_params = []
            if limit:
                query += " LIMIT %s"
                extra_params.append(limit)
            if offset:
                query += " OFFSET %s"
                extra_params.append(offset)
            params = (start_date, end_date) + tuple(extra_params)

            result = self.execute_query(query, params)

            # 转换为字典列表
            return [
                {
                    "trade_date": row[0],
                    "buy_amount": float(row[1]) if row[1] is not None else None,
                    "buy_volume": float(row[2]) if row[2] is not None else None,
                    "sell_amount": float(row[3]) if row[3] is not None else None,
                    "sell_volume": float(row[4]) if row[4] is not None else None,
                    "created_at": row[5],
                    "updated_at": row[6]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"查询港股通成交数据失败: {e}")
            raise

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """按筛选条件统计总记录数"""
        start_date = start_date or '19900101'
        end_date = end_date or '29991231'
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date >= %s AND trade_date <= %s"
        result = self.execute_query(query, (start_date, end_date))
        return int(result[0][0]) if result else 0

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取港股通成交统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = GgtDailyRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        try:
            # 默认值
            start_date = start_date or '19900101'
            end_date = end_date or '29991231'

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    AVG(buy_amount) as avg_buy_amount,
                    AVG(sell_amount) as avg_sell_amount,
                    SUM(buy_amount) as total_buy_amount,
                    SUM(sell_amount) as total_sell_amount,
                    MAX(buy_amount) as max_buy_amount,
                    MAX(sell_amount) as max_sell_amount,
                    MIN(buy_amount) as min_buy_amount,
                    MIN(sell_amount) as min_sell_amount
                FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """

            result = self.execute_query(query, (start_date, end_date))

            if result:
                row = result[0]
                return {
                    "total_count": int(row[0]) if row[0] else 0,
                    "avg_buy_amount": float(row[1]) if row[1] else 0.0,
                    "avg_sell_amount": float(row[2]) if row[2] else 0.0,
                    "total_buy_amount": float(row[3]) if row[3] else 0.0,
                    "total_sell_amount": float(row[4]) if row[4] else 0.0,
                    "max_buy_amount": float(row[5]) if row[5] else 0.0,
                    "max_sell_amount": float(row[6]) if row[6] else 0.0,
                    "min_buy_amount": float(row[7]) if row[7] else 0.0,
                    "min_sell_amount": float(row[8]) if row[8] else 0.0
                }

            return {
                "total_count": 0,
                "avg_buy_amount": 0.0,
                "avg_sell_amount": 0.0,
                "total_buy_amount": 0.0,
                "total_sell_amount": 0.0,
                "max_buy_amount": 0.0,
                "max_sell_amount": 0.0,
                "min_buy_amount": 0.0,
                "min_sell_amount": 0.0
            }

        except Exception as e:
            logger.error(f"获取港股通成交统计失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD），如果没有数据则返回 None

        Examples:
            >>> repo = GgtDailyRepository()
            >>> latest = repo.get_latest_trade_date()
            >>> print(latest)  # '20240315'
        """
        try:
            query = f"""
                SELECT trade_date
                FROM {self.TABLE_NAME}
                ORDER BY trade_date DESC
                LIMIT 1
            """

            result = self.execute_query(query)
            return result[0][0] if result else None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新港股通成交数据

        Args:
            df: 包含港股通成交数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> import pandas as pd
            >>> repo = GgtDailyRepository()
            >>> df = pd.DataFrame({
            ...     'trade_date': ['20240101', '20240102'],
            ...     'buy_amount': [30.5, 35.2],
            ...     'buy_volume': [5.2, 6.1],
            ...     'sell_amount': [28.3, 32.1],
            ...     'sell_volume': [4.8, 5.5]
            ... })
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """将pandas/numpy类型转换为Python原生类型"""
                if pd.isna(value):
                    return None
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('buy_amount')),
                    to_python_type(row.get('buy_volume')),
                    to_python_type(row.get('sell_amount')),
                    to_python_type(row.get('sell_volume'))
                ))

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, buy_amount, buy_volume, sell_amount, sell_volume, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (trade_date)
                DO UPDATE SET
                    buy_amount = EXCLUDED.buy_amount,
                    buy_volume = EXCLUDED.buy_volume,
                    sell_amount = EXCLUDED.sell_amount,
                    sell_volume = EXCLUDED.sell_volume,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条港股通成交数据")
            return count

        except Exception as e:
            logger.error(f"批量插入港股通成交数据失败: {e}")
            raise

    def get_by_trade_date(self, trade_date: str) -> List[Dict]:
        """
        按交易日期查询

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            数据列表

        Examples:
            >>> repo = GgtDailyRepository()
            >>> data = repo.get_by_trade_date('20240315')
        """
        return self.get_by_date_range(trade_date, trade_date)

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            数据是否存在

        Examples:
            >>> repo = GgtDailyRepository()
            >>> exists = repo.exists_by_date('20240315')
        """
        try:
            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE trade_date = %s
            """
            result = self.execute_query(query, (trade_date,))
            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查数据存在性失败: {e}")
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

        Examples:
            >>> repo = GgtDailyRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
        """
        try:
            start_date = start_date or '19900101'
            end_date = end_date or '29991231'

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """
            result = self.execute_query(query, (start_date, end_date))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0
