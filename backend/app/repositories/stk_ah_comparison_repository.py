"""
AH股比价数据 Repository

负责 stk_ah_comparison 表的数据访问操作
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class StkAhComparisonRepository(BaseRepository):
    """AH股比价数据仓库"""

    TABLE_NAME = "stk_ah_comparison"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkAhComparisonRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询AH股比价数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            hk_code: 港股代码
            ts_code: A股代码
            limit: 返回记录数

        Returns:
            数据列表

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> data = repo.get_by_date_range('20250812', '20250820')
        """
        query = f"""
            SELECT
                hk_code, ts_code, trade_date, hk_name, hk_pct_chg, hk_close,
                name, close, pct_chg, ah_comparison, ah_premium
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        if hk_code:
            query += " AND hk_code = %s"
            params.append(hk_code)

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY trade_date DESC, ah_premium DESC LIMIT %s OFFSET %s"
        params.append(limit)
        params.append(offset)

        result = self.execute_query(query, tuple(params))

        return [
            {
                "hk_code": row[0],
                "ts_code": row[1],
                "trade_date": row[2],
                "hk_name": row[3],
                "hk_pct_chg": float(row[4]) if row[4] is not None else None,
                "hk_close": float(row[5]) if row[5] is not None else None,
                "name": row[6],
                "close": float(row[7]) if row[7] is not None else None,
                "pct_chg": float(row[8]) if row[8] is not None else None,
                "ah_comparison": float(row[9]) if row[9] is not None else None,
                "ah_premium": float(row[10]) if row[10] is not None else None
            }
            for row in result
        ]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取AH股比价统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            统计数据字典

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> stats = repo.get_statistics('20250812', '20250820')
        """
        query = f"""
            SELECT
                COUNT(DISTINCT ts_code) as stock_count,
                AVG(ah_premium) as avg_premium,
                MAX(ah_premium) as max_premium,
                MIN(ah_premium) as min_premium,
                AVG(ah_comparison) as avg_comparison
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params) if params else None)

        if result and len(result) > 0:
            row = result[0]
            return {
                "stock_count": int(row[0]) if row[0] is not None else 0,
                "avg_premium": float(row[1]) if row[1] is not None else 0.0,
                "max_premium": float(row[2]) if row[2] is not None else 0.0,
                "min_premium": float(row[3]) if row[3] is not None else 0.0,
                "avg_comparison": float(row[4]) if row[4] is not None else 0.0
            }

        return {
            "stock_count": 0,
            "avg_premium": 0.0,
            "max_premium": 0.0,
            "min_premium": 0.0,
            "avg_comparison": 0.0
        }

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），如果没有数据则返回None

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        query = f"""
            SELECT MAX(trade_date) FROM {self.TABLE_NAME}
        """
        result = self.execute_query(query)

        if result and len(result) > 0 and result[0][0]:
            return result[0][0]

        return None

    def get_top_premium(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取溢价率最高的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD，默认最新交易日
            limit: 返回记录数

        Returns:
            数据列表

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> top20 = repo.get_top_premium('20250812', limit=20)
        """
        if not trade_date:
            trade_date = self.get_latest_trade_date()

        if not trade_date:
            return []

        query = f"""
            SELECT
                hk_code, ts_code, trade_date, hk_name, name,
                hk_close, close, ah_comparison, ah_premium
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
            ORDER BY ah_premium DESC
            LIMIT %s
        """

        result = self.execute_query(query, (trade_date, limit))

        return [
            {
                "hk_code": row[0],
                "ts_code": row[1],
                "trade_date": row[2],
                "hk_name": row[3],
                "name": row[4],
                "hk_close": float(row[5]) if row[5] is not None else None,
                "close": float(row[6]) if row[6] is not None else None,
                "ah_comparison": float(row[7]) if row[7] is not None else None,
                "ah_premium": float(row[8]) if row[8] is not None else None
            }
            for row in result
        ]

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新AH股比价数据

        Args:
            df: 包含AH股比价数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空,跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
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
                str(row.get('hk_code', '')),
                str(row.get('ts_code', '')),
                str(row.get('trade_date', '')),
                str(row.get('hk_name', '')),
                to_python_type(row.get('hk_pct_chg')),
                to_python_type(row.get('hk_close')),
                str(row.get('name', '')),
                to_python_type(row.get('close')),
                to_python_type(row.get('pct_chg')),
                to_python_type(row.get('ah_comparison')),
                to_python_type(row.get('ah_premium'))
            ))

        # 使用 UPSERT 语法
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (hk_code, ts_code, trade_date, hk_name, hk_pct_chg, hk_close,
             name, close, pct_chg, ah_comparison, ah_premium, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (hk_code, ts_code, trade_date)
            DO UPDATE SET
                hk_name = EXCLUDED.hk_name,
                hk_pct_chg = EXCLUDED.hk_pct_chg,
                hk_close = EXCLUDED.hk_close,
                name = EXCLUDED.name,
                close = EXCLUDED.close,
                pct_chg = EXCLUDED.pct_chg,
                ah_comparison = EXCLUDED.ah_comparison,
                ah_premium = EXCLUDED.ah_premium,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"成功插入/更新 {count} 条AH股比价数据")
        return count

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
            >>> repo = StkAhComparisonRepository()
            >>> count = repo.delete_by_date_range('20250812', '20250820')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """

        count = self.execute_update(query, (start_date, end_date))
        logger.info(f"删除了 {count} 条AH股比价数据")
        return count

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> exists = repo.exists_by_date('20250812')
        """
        query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """

        result = self.execute_query(query, (trade_date,))

        if result and len(result) > 0:
            return int(result[0][0]) > 0

        return False

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = StkAhComparisonRepository()
            >>> count = repo.get_record_count('20250812', '20250820')
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
        params = []

        if start_date:
            query += " AND trade_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

        result = self.execute_query(query, tuple(params) if params else None)

        if result and len(result) > 0:
            return int(result[0][0])

        return 0
