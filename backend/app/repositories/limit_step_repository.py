"""
连板天梯 Repository
"""
from typing import List, Dict, Optional
import pandas as pd
from app.repositories.base_repository import BaseRepository
from loguru import logger


class LimitStepRepository(BaseRepository):
    """连板天梯数据访问层"""

    TABLE_NAME = "limit_step"

    # 允许排序的列白名单，防止 SQL 注入
    SORTABLE_COLUMNS = {'nums'}

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ LimitStepRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> List[Dict]:
        """
        按日期范围查询连板天梯数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            nums: 连板次数（可选，如 "2" 或 "2,3"）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = LimitStepRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240115', nums='5')
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
            if nums:
                # 支持多个连板次数筛选，如 "2,3"
                nums_list = [n.strip() for n in nums.split(',')]
                placeholders = ','.join(['%s'] * len(nums_list))
                conditions.append(f"nums IN ({placeholders})")
                params.extend(nums_list)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            limit_clause = f"LIMIT {limit}" if limit else ""
            offset_clause = f"OFFSET {offset}" if offset else ""

            # 排序：仅允许白名单列，防止 SQL 注入
            order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
            if sort_by and sort_by in self.SORTABLE_COLUMNS:
                order_clause = f"ORDER BY CAST({sort_by} AS INTEGER) {order} NULLS LAST, trade_date DESC, ts_code"
            else:
                order_clause = "ORDER BY trade_date DESC, CAST(nums AS INTEGER) DESC, ts_code"

            query = f"""
                SELECT
                    trade_date, ts_code, name, nums
                FROM {self.TABLE_NAME}
                {where_clause}
                {order_clause}
                {limit_clause}
                {offset_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询连板天梯数据失败: {e}")
            raise

    def get_by_trade_date(self, trade_date: str) -> List[Dict]:
        """
        按交易日期查询连板天梯数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            数据列表

        Examples:
            >>> repo = LimitStepRepository()
            >>> data = repo.get_by_trade_date('20240115')
        """
        return self.get_by_date_range(
            start_date=trade_date,
            end_date=trade_date
        )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取连板天梯统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = LimitStepRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
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

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                SELECT
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(*) as total_records,
                    MAX(CAST(nums AS INTEGER)) as max_nums,
                    AVG(CAST(nums AS INTEGER)) as avg_nums,
                    MIN(CAST(nums AS INTEGER)) as min_nums,
                    COUNT(DISTINCT trade_date) as trade_date_count
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            if result and len(result) > 0:
                row = result[0]
                return {
                    'stock_count': row[0] or 0,
                    'total_records': row[1] or 0,
                    'max_nums': row[2] or 0,
                    'avg_nums': float(row[3]) if row[3] else 0.0,
                    'min_nums': row[4] or 0,
                    'trade_date_count': row[5] or 0
                }
            return {
                'stock_count': 0,
                'total_records': 0,
                'max_nums': 0,
                'avg_nums': 0.0,
                'min_nums': 0,
                'trade_date_count': 0
            }

        except Exception as e:
            logger.error(f"获取连板天梯统计信息失败: {e}")
            raise

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None
    ) -> int:
        """
        获取符合条件的总记录数（用于分页）

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            nums: 连板次数（可选）

        Returns:
            总记录数
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
            if nums:
                nums_list = [n.strip() for n in nums.split(',')]
                placeholders = ','.join(['%s'] * len(nums_list))
                conditions.append(f"nums IN ({placeholders})")
                params.extend(nums_list)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} {where_clause}"
            result = self.execute_query(query, tuple(params) if params else None)
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取总记录数失败: {e}")
            return 0

    def get_top_by_nums(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20,
        ascending: bool = False
    ) -> List[Dict]:
        """
        按连板次数排名获取数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            limit: 返回记录数
            ascending: 是否升序（False=降序，True=升序）

        Returns:
            数据列表

        Examples:
            >>> repo = LimitStepRepository()
            >>> top20 = repo.get_top_by_nums('20240115', limit=20)
            >>> bottom10 = repo.get_top_by_nums('20240115', limit=10, ascending=True)
        """
        try:
            where_clause = f"WHERE trade_date = %s" if trade_date else ""
            order = "ASC" if ascending else "DESC"

            query = f"""
                SELECT
                    trade_date, ts_code, name, nums
                FROM {self.TABLE_NAME}
                {where_clause}
                ORDER BY CAST(nums AS INTEGER) {order}, ts_code
                LIMIT {limit}
            """

            params = (trade_date,) if trade_date else None
            result = self.execute_query(query, params)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"按连板次数排名查询失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），无数据时返回None

        Examples:
            >>> repo = LimitStepRepository()
            >>> latest = repo.get_latest_trade_date()
            >>> print(latest)  # '20240131'
        """
        try:
            query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
            result = self.execute_query(query)
            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新连板天梯数据

        Args:
            df: pandas DataFrame，包含连板天梯数据

        Returns:
            插入/更新的记录数

        Examples:
            >>> import pandas as pd
            >>> repo = LimitStepRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df.empty:
            logger.warning("DataFrame is empty, skipping upsert")
            return 0

        try:
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
                return str(value) if value is not None else None

            # 准备数据
            records = []
            for _, row in df.iterrows():
                record = (
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('nums'))
                )
                records.append(record)

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    trade_date, ts_code, name, nums
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    nums = EXCLUDED.nums,
                    updated_at = NOW()
            """

            affected_rows = self.execute_batch(query, records)
            logger.info(f"✓ 批量 UPSERT {affected_rows} 条连板天梯记录")
            return affected_rows

        except Exception as e:
            logger.error(f"批量 UPSERT 连板天梯数据失败: {e}")
            raise

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
            >>> repo = LimitStepRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """
            affected_rows = self.execute_update(query, (start_date, end_date))
            logger.info(f"✓ 删除 {affected_rows} 条连板天梯记录")
            return affected_rows

        except Exception as e:
            logger.error(f"删除连板天梯数据失败: {e}")
            raise

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期是否有数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            存在返回True，否则返回False

        Examples:
            >>> repo = LimitStepRepository()
            >>> if repo.exists_by_date('20240115'):
            >>>     print("数据已存在")
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date = %s"
            result = self.execute_query(query, (trade_date,))
            return result[0][0] > 0 if result else False

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
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = LimitStepRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
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

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} {where_clause}"
            result = self.execute_query(query, tuple(params) if params else None)
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'name': row[2],
            'nums': row[3]
        }
