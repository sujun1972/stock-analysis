"""
复权因子数据 Repository

负责 adj_factor 表的数据访问操作
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class AdjFactorRepository(BaseRepository):
    """复权因子数据仓库"""

    TABLE_NAME = "adj_factor"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ AdjFactorRepository initialized")

    def get_total_count(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """按条件查询总记录数"""
        conditions = []
        params = []

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} {where_clause}"
        result = self.execute_query(query, tuple(params) if params else None)
        return result[0][0] if result else 0

    def get_by_code_and_date_range(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按股票代码和日期范围查询复权因子数据

        Args:
            ts_code: 股票代码（可选，如 000001.SZ）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            limit: 返回记录数限制（可选）

        Returns:
            复权因子数据列表

        Examples:
            >>> repo = AdjFactorRepository()
            >>> # 查询单只股票的全部复权因子
            >>> data = repo.get_by_code_and_date_range(ts_code='000001.SZ')
            >>> # 查询单日全部股票的复权因子
            >>> data = repo.get_by_code_and_date_range(start_date='20240101', end_date='20240101')
        """
        conditions = []
        params = []

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset > 0 else ""

        query = f"""
            SELECT
                ts_code,
                trade_date,
                adj_factor,
                created_at,
                updated_at
            FROM {self.TABLE_NAME}
            {where_clause}
            ORDER BY trade_date DESC, ts_code
            {limit_clause}
            {offset_clause}
        """

        result = self.execute_query(query, tuple(params) if params else None)
        return [self._row_to_dict(row) for row in result]

    def get_latest_by_code(self, ts_code: str) -> Optional[Dict]:
        """
        获取指定股票的最新复权因子

        Args:
            ts_code: 股票代码

        Returns:
            最新复权因子数据，如果不存在返回 None

        Examples:
            >>> repo = AdjFactorRepository()
            >>> latest = repo.get_latest_by_code('000001.SZ')
            >>> if latest:
            >>>     print(f"最新复权因子: {latest['adj_factor']}, 日期: {latest['trade_date']}")
        """
        query = f"""
            SELECT
                ts_code,
                trade_date,
                adj_factor,
                created_at,
                updated_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
            ORDER BY trade_date DESC
            LIMIT 1
        """

        result = self.execute_query(query, (ts_code,))
        if result:
            return self._row_to_dict(result[0])
        return None

    def get_statistics(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取复权因子统计信息

        Args:
            ts_code: 股票代码（可选）
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）

        Returns:
            统计信息字典，包含：
            - total_records: 总记录数
            - stock_count: 股票数量（如果未指定 ts_code）
            - min_factor: 最小复权因子
            - max_factor: 最大复权因子
            - avg_factor: 平均复权因子
            - latest_date: 最新日期

        Examples:
            >>> repo = AdjFactorRepository()
            >>> stats = repo.get_statistics(start_date='20240101', end_date='20240131')
        """
        conditions = []
        params = []

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ts_code) as stock_count,
                MIN(adj_factor) as min_factor,
                MAX(adj_factor) as max_factor,
                AVG(adj_factor) as avg_factor,
                MAX(trade_date) as latest_date
            FROM {self.TABLE_NAME}
            {where_clause}
        """

        result = self.execute_query(query, tuple(params) if params else None)
        if result:
            row = result[0]
            # 处理 latest_date：可能是 datetime.date 对象
            latest_date = row[5]
            if latest_date and hasattr(latest_date, 'strftime'):
                latest_date = latest_date.strftime('%Y%m%d')

            return {
                'total_records': int(row[0]) if row[0] else 0,
                'stock_count': int(row[1]) if row[1] else 0,
                'min_factor': float(row[2]) if row[2] else None,
                'max_factor': float(row[3]) if row[3] else None,
                'avg_factor': float(row[4]) if row[4] else None,
                'latest_date': latest_date
            }
        return {}

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入或更新复权因子数据

        Args:
            df: 包含复权因子数据的 DataFrame，必须包含以下列：
                - ts_code: 股票代码
                - trade_date: 交易日期 YYYYMMDD
                - adj_factor: 复权因子

        Returns:
            成功插入/更新的记录数

        Examples:
            >>> import pandas as pd
            >>> repo = AdjFactorRepository()
            >>> df = pd.DataFrame({
            >>>     'ts_code': ['000001.SZ', '000002.SZ'],
            >>>     'trade_date': ['20240101', '20240101'],
            >>>     'adj_factor': [108.031, 95.234]
            >>> })
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """
            将pandas/numpy类型转换为Python原生类型

            ⚠️ 关键问题：psycopg2无法直接处理numpy类型（numpy.int64, numpy.float64等）
            必须转换为Python原生类型（int, float, None）
            否则会报错：can't adapt type 'numpy.int64' 或 integer out of range
            """
            if pd.isna(value):
                return None
            # 转换numpy整数类型为Python int
            if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            # 转换numpy浮点类型为Python float
            if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                return float(value)
            return value

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, trade_date, adj_factor)
            VALUES (%s, %s, %s)
            ON CONFLICT (ts_code, trade_date)
            DO UPDATE SET
                adj_factor = EXCLUDED.adj_factor,
                updated_at = CURRENT_TIMESTAMP
        """

        # 准备插入数据（对每个字段应用类型转换）
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('adj_factor')),
            ))

        try:
            # 使用 executemany 批量插入
            count = self.execute_batch(query, values)
            logger.info(f"✓ 批量插入/更新 {count} 条复权因子数据")
            return count
        except Exception as e:
            logger.error(f"批量插入复权因子数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围的复权因子数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = AdjFactorRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        conditions = ["trade_date >= %s", "trade_date <= %s"]
        params = [start_date, end_date]

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE {' AND '.join(conditions)}
        """

        try:
            count = self.execute_update(query, tuple(params))
            logger.info(f"✓ 删除 {count} 条复权因子数据")
            return count
        except Exception as e:
            logger.error(f"删除复权因子数据失败: {e}")
            raise

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的复权因子数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            如果数据存在返回 True，否则返回 False

        Examples:
            >>> repo = AdjFactorRepository()
            >>> exists = repo.exists_by_date('20240101')
        """
        conditions = ["trade_date = %s"]
        params = [trade_date]

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            WHERE {' AND '.join(conditions)}
        """

        result = self.execute_query(query, tuple(params))
        return result[0][0] > 0 if result else False

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取指定条件的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD（可选）
            end_date: 结束日期，格式：YYYYMMDD（可选）
            ts_code: 股票代码（可选）

        Returns:
            记录数

        Examples:
            >>> repo = AdjFactorRepository()
            >>> count = repo.get_record_count(start_date='20240101', end_date='20240131')
        """
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

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            {where_clause}
        """

        result = self.execute_query(query, tuple(params) if params else None)
        return result[0][0] if result else 0

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        # 处理 trade_date：可能是 VARCHAR 返回字符串，或 DATE 返回 datetime.date 对象
        trade_date = row[1]
        if hasattr(trade_date, 'strftime'):
            trade_date = trade_date.strftime('%Y%m%d')

        return {
            'ts_code': row[0],
            'trade_date': trade_date,
            'adj_factor': float(row[2]) if row[2] is not None else None,
            'created_at': row[3].isoformat() if row[3] else None,
            'updated_at': row[4].isoformat() if row[4] else None
        }
