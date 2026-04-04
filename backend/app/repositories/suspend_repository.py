"""
停复牌信息数据访问层
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class SuspendRepository(BaseRepository):
    """停复牌信息数据访问"""

    TABLE_NAME = "suspend_d"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ SuspendRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        suspend_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询停复牌信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            suspend_type: 停复牌类型，S-停牌，R-复牌（可选）
            limit: 返回记录数限制
            offset: 跳过的记录数（用于分页）

        Returns:
            停复牌信息列表

        Examples:
            >>> repo = SuspendRepository()
            >>> data = repo.get_by_date_range('20240301', '20240331', ts_code='000001.SZ', limit=30, offset=0)
        """
        query = f"""
            SELECT ts_code, trade_date, suspend_timing, suspend_type,
                   created_at, updated_at
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
        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)
        if suspend_type:
            query += " AND suspend_type = %s"
            params.append(suspend_type)

        query += " ORDER BY trade_date DESC, ts_code"

        if limit:
            query += " LIMIT %s"
            params.append(limit)
        if offset:
            query += " OFFSET %s"
            params.append(offset)

        try:
            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询停复牌信息失败: {e}")
            raise

    def count_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        suspend_type: Optional[str] = None
    ) -> int:
        """
        统计日期范围内的停复牌记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            suspend_type: 停复牌类型，S-停牌，R-复牌（可选）

        Returns:
            记录总数

        Examples:
            >>> repo = SuspendRepository()
            >>> total = repo.count_by_date_range('20240301', '20240331')
        """
        query = f"""
            SELECT COUNT(*) as count
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
        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)
        if suspend_type:
            query += " AND suspend_type = %s"
            params.append(suspend_type)

        try:
            result = self.execute_query(query, tuple(params))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"统计停复牌记录数失败: {e}")
            raise

    def get_by_trade_date(
        self,
        trade_date: str,
        suspend_type: Optional[str] = None
    ) -> List[Dict]:
        """
        查询指定交易日的停复牌信息

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            suspend_type: 停复牌类型，S-停牌，R-复牌（可选）

        Returns:
            停复牌信息列表

        Examples:
            >>> repo = SuspendRepository()
            >>> suspends = repo.get_by_trade_date('20240315', suspend_type='S')
        """
        query = f"""
            SELECT ts_code, trade_date, suspend_timing, suspend_type,
                   created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """

        params = [trade_date]

        if suspend_type:
            query += " AND suspend_type = %s"
            params.append(suspend_type)

        query += " ORDER BY ts_code"

        try:
            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询停复牌信息失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取停复牌统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = SuspendRepository()
            >>> stats = repo.get_statistics('20240301', '20240331')
        """
        query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(DISTINCT trade_date) as trade_date_count,
                SUM(CASE WHEN suspend_type = 'S' THEN 1 ELSE 0 END) as suspend_count,
                SUM(CASE WHEN suspend_type = 'R' THEN 1 ELSE 0 END) as resume_count
            FROM {self.TABLE_NAME}
        """

        params = []

        if start_date and end_date:
            query += " WHERE trade_date >= %s AND trade_date <= %s"
            params.extend([start_date, end_date])
        elif start_date:
            query += " WHERE trade_date >= %s"
            params.append(start_date)
        elif end_date:
            query += " WHERE trade_date <= %s"
            params.append(end_date)

        try:
            result = self.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    'total_count': row[0] or 0,
                    'stock_count': row[1] or 0,
                    'trade_date_count': row[2] or 0,
                    'suspend_count': row[3] or 0,
                    'resume_count': row[4] or 0
                }
            return {
                'total_count': 0,
                'stock_count': 0,
                'trade_date_count': 0,
                'suspend_count': 0,
                'resume_count': 0
            }
        except Exception as e:
            logger.error(f"获取停复牌统计信息失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），如果没有数据则返回None

        Examples:
            >>> repo = SuspendRepository()
            >>> latest = repo.get_latest_trade_date()
            >>> print(latest)  # '20240315'
        """
        query = f"""
            SELECT trade_date
            FROM {self.TABLE_NAME}
            ORDER BY trade_date DESC
            LIMIT 1
        """

        try:
            result = self.execute_query(query)
            if result and len(result) > 0:
                return result[0][0]
            return None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = SuspendRepository()
            >>> exists = repo.exists_by_date('20240315')
        """
        query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """

        try:
            result = self.execute_query(query, (trade_date,))
            return result[0][0] > 0 if result else False
        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新停复牌信息

        使用 ON CONFLICT DO UPDATE 实现 UPSERT 语义

        Args:
            df: 包含停复牌信息的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = SuspendRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

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
            return str(value) if value is not None else None

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, trade_date, suspend_timing, suspend_type, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ts_code, trade_date)
            DO UPDATE SET
                suspend_timing = EXCLUDED.suspend_timing,
                suspend_type = EXCLUDED.suspend_type,
                updated_at = NOW()
        """

        # 准备批量插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('suspend_timing')),
                to_python_type(row.get('suspend_type'))
            ))

        try:
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条停复牌记录")
            return count
        except Exception as e:
            logger.error(f"批量插入停复牌信息失败: {e}")
            raise

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        删除指定日期范围的停复牌信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = SuspendRepository()
            >>> count = repo.delete_by_date_range('20240301', '20240331')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """

        try:
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"成功删除 {count} 条停复牌记录")
            return count
        except Exception as e:
            logger.error(f"删除停复牌信息失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'trade_date': row[1],
            'suspend_timing': row[2],
            'suspend_type': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
            'updated_at': row[5].isoformat() if row[5] else None
        }
