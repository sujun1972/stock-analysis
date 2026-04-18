"""
龙虎榜每日明细 Repository
"""
from typing import List, Dict, Optional
from app.repositories.base_repository import BaseRepository
from loguru import logger


class TopListRepository(BaseRepository):
    """龙虎榜每日明细数据访问层"""

    TABLE_NAME = "top_list"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ TopListRepository initialized")

    # 允许排序的列白名单，防止 SQL 注入
    SORTABLE_COLUMNS = {'pct_change', 'turnover_rate', 'amount', 'net_amount', 'l_amount'}

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc'
    ) -> List[Dict]:
        """
        按日期范围查询龙虎榜数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = TopListRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240115', ts_code='000001.SZ')
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

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            limit_clause = f"LIMIT {self._enforce_limit(limit)}"
            offset_clause = f"OFFSET {int(offset)}" if offset else ""

            # 排序：仅允许白名单列，防止 SQL 注入
            order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
            if sort_by and sort_by in self.SORTABLE_COLUMNS:
                order_clause = f"ORDER BY {sort_by} {order} NULLS LAST"
            else:
                order_clause = "ORDER BY trade_date DESC, net_amount DESC"

            query = f"""
                SELECT
                    trade_date, ts_code, name, close, pct_change,
                    turnover_rate, amount, l_sell, l_buy, l_amount,
                    net_amount, net_rate, amount_rate, float_values, reason
                FROM {self.TABLE_NAME}
                {where_clause}
                {order_clause}
                {limit_clause}
                {offset_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询龙虎榜数据失败: {e}")
            raise

    def get_by_trade_date(self, trade_date: str) -> List[Dict]:
        """
        按交易日期查询龙虎榜数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            数据列表

        Examples:
            >>> repo = TopListRepository()
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
        获取龙虎榜统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = TopListRepository()
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
                    AVG(net_amount) as avg_net_amount,
                    SUM(net_amount) as total_net_amount,
                    MAX(net_amount) as max_net_amount,
                    MIN(net_amount) as min_net_amount,
                    AVG(amount) as avg_amount,
                    AVG(pct_change) as avg_pct_change
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            if result and len(result) > 0:
                row = result[0]
                return {
                    'stock_count': row[0] or 0,
                    'total_records': row[1] or 0,
                    'avg_net_amount': float(row[2]) if row[2] else 0.0,
                    'total_net_amount': float(row[3]) if row[3] else 0.0,
                    'max_net_amount': float(row[4]) if row[4] else 0.0,
                    'min_net_amount': float(row[5]) if row[5] else 0.0,
                    'avg_amount': float(row[6]) if row[6] else 0.0,
                    'avg_pct_change': float(row[7]) if row[7] else 0.0
                }
            return {
                'stock_count': 0,
                'total_records': 0,
                'avg_net_amount': 0.0,
                'total_net_amount': 0.0,
                'max_net_amount': 0.0,
                'min_net_amount': 0.0,
                'avg_amount': 0.0,
                'avg_pct_change': 0.0
            }

        except Exception as e:
            logger.error(f"获取龙虎榜统计信息失败: {e}")
            raise

    def get_top_by_net_amount(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20,
        ascending: bool = False
    ) -> List[Dict]:
        """
        按净买入额排名获取龙虎榜数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选）
            limit: 返回记录数
            ascending: 是否升序（False=降序，True=升序）

        Returns:
            数据列表

        Examples:
            >>> repo = TopListRepository()
            >>> top20 = repo.get_top_by_net_amount('20240115', limit=20)
            >>> bottom10 = repo.get_top_by_net_amount('20240115', limit=10, ascending=True)
        """
        try:
            where_clause = f"WHERE trade_date = %s" if trade_date else ""
            order = "ASC" if ascending else "DESC"

            query = f"""
                SELECT
                    trade_date, ts_code, name, close, pct_change,
                    turnover_rate, amount, l_sell, l_buy, l_amount,
                    net_amount, net_rate, amount_rate, float_values, reason
                FROM {self.TABLE_NAME}
                {where_clause}
                ORDER BY net_amount {order}
                LIMIT {limit}
            """

            params = (trade_date,) if trade_date else None
            result = self.execute_query(query, params)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"按净买入额排名查询失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），无数据时返回None

        Examples:
            >>> repo = TopListRepository()
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

    def bulk_upsert(self, df) -> int:
        """
        批量插入/更新龙虎榜数据

        Args:
            df: pandas DataFrame，包含龙虎榜数据

        Returns:
            插入/更新的记录数

        Examples:
            >>> import pandas as pd
            >>> repo = TopListRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df.empty:
            logger.warning("DataFrame is empty, skipping upsert")
            return 0

        try:
            # 列名映射
            column_mapping = {
                'trade_date': 'trade_date',
                'ts_code': 'ts_code',
                'name': 'name',
                'close': 'close',
                'pct_change': 'pct_change',
                'turnover_rate': 'turnover_rate',
                'amount': 'amount',
                'l_sell': 'l_sell',
                'l_buy': 'l_buy',
                'l_amount': 'l_amount',
                'net_amount': 'net_amount',
                'net_rate': 'net_rate',
                'amount_rate': 'amount_rate',
                'float_values': 'float_values',
                'reason': 'reason'
            }

            # 准备数据
            records = []
            for _, row in df.iterrows():
                record = tuple(
                    row.get(col) for col in column_mapping.keys()
                )
                records.append(record)

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    trade_date, ts_code, name, close, pct_change,
                    turnover_rate, amount, l_sell, l_buy, l_amount,
                    net_amount, net_rate, amount_rate, float_values, reason
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    close = EXCLUDED.close,
                    pct_change = EXCLUDED.pct_change,
                    turnover_rate = EXCLUDED.turnover_rate,
                    amount = EXCLUDED.amount,
                    l_sell = EXCLUDED.l_sell,
                    l_buy = EXCLUDED.l_buy,
                    l_amount = EXCLUDED.l_amount,
                    net_amount = EXCLUDED.net_amount,
                    net_rate = EXCLUDED.net_rate,
                    amount_rate = EXCLUDED.amount_rate,
                    float_values = EXCLUDED.float_values,
                    reason = EXCLUDED.reason,
                    updated_at = NOW()
            """

            affected_rows = self.execute_batch(query, records)
            logger.info(f"✓ 批量 UPSERT {affected_rows} 条龙虎榜记录")
            return affected_rows

        except Exception as e:
            logger.error(f"批量 UPSERT 龙虎榜数据失败: {e}")
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
            >>> repo = TopListRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """
            affected_rows = self.execute_update(query, (start_date, end_date))
            logger.info(f"✓ 删除 {affected_rows} 条龙虎榜记录")
            return affected_rows

        except Exception as e:
            logger.error(f"删除龙虎榜数据失败: {e}")
            raise

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期是否有数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            存在返回True，否则返回False

        Examples:
            >>> repo = TopListRepository()
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
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = TopListRepository()
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
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

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
            'close': float(row[3]) if row[3] is not None else None,
            'pct_change': float(row[4]) if row[4] is not None else None,
            'turnover_rate': float(row[5]) if row[5] is not None else None,
            'amount': float(row[6]) if row[6] is not None else None,
            'l_sell': float(row[7]) if row[7] is not None else None,
            'l_buy': float(row[8]) if row[8] is not None else None,
            'l_amount': float(row[9]) if row[9] is not None else None,
            'net_amount': float(row[10]) if row[10] is not None else None,
            'net_rate': float(row[11]) if row[11] is not None else None,
            'amount_rate': float(row[12]) if row[12] is not None else None,
            'float_values': float(row[13]) if row[13] is not None else None,
            'reason': row[14]
        }
