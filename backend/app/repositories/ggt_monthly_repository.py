"""
港股通每月成交统计 Repository

职责:
- 管理 ggt_monthly 表的数据访问
- 提供查询、统计、插入/更新功能
"""

import pandas as pd
from typing import List, Dict, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository


class GgtMonthlyRepository(BaseRepository):
    """港股通每月成交统计数据访问层"""

    TABLE_NAME = "ggt_monthly"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ GgtMonthlyRepository initialized")

    def get_by_month_range(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按月度范围查询港股通成交数据

        Args:
            start_month: 开始月度,格式:YYYYMM(可选,默认'190001')
            end_month: 结束月度,格式:YYYYMM(可选,默认'299912')
            limit: 返回记录数限制(可选)

        Returns:
            数据列表

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> data = repo.get_by_month_range('202401', '202412', 30)
        """
        try:
            # 默认值
            start_month = start_month or '190001'
            end_month = end_month or '299912'

            query = f"""
                SELECT month, day_buy_amt, day_buy_vol, day_sell_amt, day_sell_vol,
                       total_buy_amt, total_buy_vol, total_sell_amt, total_sell_vol,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE month >= %s AND month <= %s
                ORDER BY month DESC
            """

            extra_params = []
            if limit:
                query += " LIMIT %s"
                extra_params.append(limit)
            if offset:
                query += " OFFSET %s"
                extra_params.append(offset)
            params = (start_month, end_month) + tuple(extra_params)

            result = self.execute_query(query, params)

            # 转换为字典列表
            return [
                {
                    "month": row[0],
                    "day_buy_amt": float(row[1]) if row[1] is not None else None,
                    "day_buy_vol": float(row[2]) if row[2] is not None else None,
                    "day_sell_amt": float(row[3]) if row[3] is not None else None,
                    "day_sell_vol": float(row[4]) if row[4] is not None else None,
                    "total_buy_amt": float(row[5]) if row[5] is not None else None,
                    "total_buy_vol": float(row[6]) if row[6] is not None else None,
                    "total_sell_amt": float(row[7]) if row[7] is not None else None,
                    "total_sell_vol": float(row[8]) if row[8] is not None else None,
                    "created_at": row[9],
                    "updated_at": row[10]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"查询港股通每月成交数据失败: {e}")
            raise

    def get_total_count(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> int:
        """按筛选条件统计总记录数"""
        start_month = start_month or '190001'
        end_month = end_month or '299912'
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE month >= %s AND month <= %s"
        result = self.execute_query(query, (start_month, end_month))
        return int(result[0][0]) if result else 0

    def get_statistics(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> Dict:
        """
        获取港股通每月成交统计信息

        Args:
            start_month: 开始月度,格式:YYYYMM(可选)
            end_month: 结束月度,格式:YYYYMM(可选)

        Returns:
            统计信息字典

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> stats = repo.get_statistics('202401', '202412')
        """
        try:
            # 默认值
            start_month = start_month or '190001'
            end_month = end_month or '299912'

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    AVG(day_buy_amt) as avg_day_buy_amt,
                    AVG(day_sell_amt) as avg_day_sell_amt,
                    SUM(total_buy_amt) as sum_total_buy_amt,
                    SUM(total_sell_amt) as sum_total_sell_amt,
                    MAX(total_buy_amt) as max_total_buy_amt,
                    MAX(total_sell_amt) as max_total_sell_amt,
                    MIN(total_buy_amt) as min_total_buy_amt,
                    MIN(total_sell_amt) as min_total_sell_amt
                FROM {self.TABLE_NAME}
                WHERE month >= %s AND month <= %s
            """

            result = self.execute_query(query, (start_month, end_month))

            if result:
                row = result[0]
                return {
                    "total_count": int(row[0]) if row[0] else 0,
                    "avg_day_buy_amt": float(row[1]) if row[1] else 0.0,
                    "avg_day_sell_amt": float(row[2]) if row[2] else 0.0,
                    "sum_total_buy_amt": float(row[3]) if row[3] else 0.0,
                    "sum_total_sell_amt": float(row[4]) if row[4] else 0.0,
                    "max_total_buy_amt": float(row[5]) if row[5] else 0.0,
                    "max_total_sell_amt": float(row[6]) if row[6] else 0.0,
                    "min_total_buy_amt": float(row[7]) if row[7] else 0.0,
                    "min_total_sell_amt": float(row[8]) if row[8] else 0.0
                }

            return {
                "total_count": 0,
                "avg_day_buy_amt": 0.0,
                "avg_day_sell_amt": 0.0,
                "sum_total_buy_amt": 0.0,
                "sum_total_sell_amt": 0.0,
                "max_total_buy_amt": 0.0,
                "max_total_sell_amt": 0.0,
                "min_total_buy_amt": 0.0,
                "min_total_sell_amt": 0.0
            }

        except Exception as e:
            logger.error(f"获取港股通每月成交统计失败: {e}")
            raise

    def get_latest_month(self) -> Optional[str]:
        """
        获取最新月度

        Returns:
            最新月度(YYYYMM),如果没有数据则返回 None

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> latest = repo.get_latest_month()
            >>> print(latest)  # '202403'
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
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新港股通每月成交数据

        Args:
            df: 包含港股通每月成交数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> import pandas as pd
            >>> repo = GgtMonthlyRepository()
            >>> df = pd.DataFrame({
            ...     'month': ['202401', '202402'],
            ...     'day_buy_amt': [37.77, 34.70],
            ...     'day_buy_vol': [6.73, 5.15],
            ...     'day_sell_amt': [21.84, 30.07],
            ...     'day_sell_vol': [4.69, 5.15],
            ...     'total_buy_amt': [754.77, 601.37],
            ...     'total_buy_vol': [134.42, 102.96],
            ...     'total_sell_amt': [450.97, 601.37],
            ...     'total_sell_vol': [96.62, 102.96]
            ... })
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空,跳过插入")
            return 0

        try:
            # 辅助函数:将pandas/numpy类型转换为Python原生类型
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
                    to_python_type(row.get('month')),
                    to_python_type(row.get('day_buy_amt')),
                    to_python_type(row.get('day_buy_vol')),
                    to_python_type(row.get('day_sell_amt')),
                    to_python_type(row.get('day_sell_vol')),
                    to_python_type(row.get('total_buy_amt')),
                    to_python_type(row.get('total_buy_vol')),
                    to_python_type(row.get('total_sell_amt')),
                    to_python_type(row.get('total_sell_vol'))
                ))

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (month, day_buy_amt, day_buy_vol, day_sell_amt, day_sell_vol,
                 total_buy_amt, total_buy_vol, total_sell_amt, total_sell_vol, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (month)
                DO UPDATE SET
                    day_buy_amt = EXCLUDED.day_buy_amt,
                    day_buy_vol = EXCLUDED.day_buy_vol,
                    day_sell_amt = EXCLUDED.day_sell_amt,
                    day_sell_vol = EXCLUDED.day_sell_vol,
                    total_buy_amt = EXCLUDED.total_buy_amt,
                    total_buy_vol = EXCLUDED.total_buy_vol,
                    total_sell_amt = EXCLUDED.total_sell_amt,
                    total_sell_vol = EXCLUDED.total_sell_vol,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条港股通每月成交数据")
            return count

        except Exception as e:
            logger.error(f"批量插入港股通每月成交数据失败: {e}")
            raise

    def get_by_month(self, month: str) -> List[Dict]:
        """
        按月度查询

        Args:
            month: 月度,格式:YYYYMM

        Returns:
            数据列表

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> data = repo.get_by_month('202403')
        """
        return self.get_by_month_range(month, month)

    def exists_by_month(self, month: str) -> bool:
        """
        检查指定月度的数据是否存在

        Args:
            month: 月度,格式:YYYYMM

        Returns:
            数据是否存在

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> exists = repo.exists_by_month('202403')
        """
        try:
            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE month = %s
            """
            result = self.execute_query(query, (month,))
            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查数据存在性失败: {e}")
            return False

    def get_record_count(
        self,
        start_month: Optional[str] = None,
        end_month: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_month: 开始月度,格式:YYYYMM(可选)
            end_month: 结束月度,格式:YYYYMM(可选)

        Returns:
            记录数

        Examples:
            >>> repo = GgtMonthlyRepository()
            >>> count = repo.get_record_count('202401', '202412')
        """
        try:
            start_month = start_month or '190001'
            end_month = end_month or '299912'

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE month >= %s AND month <= %s
            """
            result = self.execute_query(query, (start_month, end_month))
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0
