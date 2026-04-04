"""
港股通十大成交股 Repository

管理 ggt_top10 表的数据访问
根据Tushare ggt_top10接口返回数据
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class GgtTop10Repository(BaseRepository):
    """港股通十大成交股数据仓库"""

    TABLE_NAME = "ggt_top10"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ GgtTop10Repository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询港股通十大成交股数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            market_type: 市场类型 2:港股通(沪) 4:港股通(深)（可选）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = GgtTop10Repository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
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
        if market_type:
            conditions.append("market_type = %s")
            params.append(market_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                trade_date,
                ts_code,
                name,
                close,
                p_change,
                rank,
                market_type,
                amount,
                net_amount,
                sh_amount,
                sh_net_amount,
                sh_buy,
                sh_sell,
                sz_amount,
                sz_net_amount,
                sz_buy,
                sz_sell
            FROM {self.TABLE_NAME}
            {where_clause}
            ORDER BY trade_date DESC, rank ASC
        """

        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        result = self.execute_query(query, tuple(params) if params else None)
        return [self._row_to_dict(row) for row in result]

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> int:
        """按筛选条件统计总记录数"""
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
        if market_type:
            conditions.append("market_type = %s")
            params.append(market_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} {where_clause}"
        result = self.execute_query(query, tuple(params) if params else None)
        return int(result[0][0]) if result else 0

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            market_type: 市场类型（可选）

        Returns:
            统计数据字典

        Examples:
            >>> repo = GgtTop10Repository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("trade_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("trade_date <= %s")
            params.append(end_date)
        if market_type:
            conditions.append("market_type = %s")
            params.append(market_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT trade_date) as trading_days,
                COUNT(DISTINCT ts_code) as stock_count,
                AVG(amount) as avg_amount,
                AVG(net_amount) as avg_net_amount,
                MAX(amount) as max_amount,
                MIN(amount) as min_amount,
                SUM(net_amount) as total_net_amount
            FROM {self.TABLE_NAME}
            {where_clause}
        """

        result = self.execute_query(query, tuple(params) if params else None)
        if result:
            row = result[0]
            return {
                'total_records': row[0] or 0,
                'trading_days': row[1] or 0,
                'stock_count': row[2] or 0,
                'avg_amount': float(row[3]) if row[3] else 0,
                'avg_net_amount': float(row[4]) if row[4] else 0,
                'max_amount': float(row[5]) if row[5] else 0,
                'min_amount': float(row[6]) if row[6] else 0,
                'total_net_amount': float(row[7]) if row[7] else 0
            }
        return {}

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期，格式：YYYYMMDD

        Examples:
            >>> repo = GgtTop10Repository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        query = f"""
            SELECT MAX(trade_date) as latest_date
            FROM {self.TABLE_NAME}
        """

        result = self.execute_query(query)
        if result and result[0][0]:
            return result[0][0]
        return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新数据（UPSERT）

        Args:
            df: 包含数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = GgtTop10Repository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
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
            return value

        # 准备插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('name')),
                to_python_type(row.get('close')),
                to_python_type(row.get('p_change')),
                to_python_type(row.get('rank')),
                to_python_type(row.get('market_type')),
                to_python_type(row.get('amount')),
                to_python_type(row.get('net_amount')),
                to_python_type(row.get('sh_amount')),
                to_python_type(row.get('sh_net_amount')),
                to_python_type(row.get('sh_buy')),
                to_python_type(row.get('sh_sell')),
                to_python_type(row.get('sz_amount')),
                to_python_type(row.get('sz_net_amount')),
                to_python_type(row.get('sz_buy')),
                to_python_type(row.get('sz_sell'))
            ))

        # UPSERT查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (trade_date, ts_code, name, close, p_change, rank, market_type,
             amount, net_amount, sh_amount, sh_net_amount, sh_buy, sh_sell,
             sz_amount, sz_net_amount, sz_buy, sz_sell)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, ts_code, market_type)
            DO UPDATE SET
                name = EXCLUDED.name,
                close = EXCLUDED.close,
                p_change = EXCLUDED.p_change,
                rank = EXCLUDED.rank,
                amount = EXCLUDED.amount,
                net_amount = EXCLUDED.net_amount,
                sh_amount = EXCLUDED.sh_amount,
                sh_net_amount = EXCLUDED.sh_net_amount,
                sh_buy = EXCLUDED.sh_buy,
                sh_sell = EXCLUDED.sh_sell,
                sz_amount = EXCLUDED.sz_amount,
                sz_net_amount = EXCLUDED.sz_net_amount,
                sz_buy = EXCLUDED.sz_buy,
                sz_sell = EXCLUDED.sz_sell,
                updated_at = CURRENT_TIMESTAMP
        """

        count = self.execute_batch(query, values)
        logger.info(f"✓ 批量插入/更新 {count} 条记录到 {self.TABLE_NAME}")
        return count

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = GgtTop10Repository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """

        count = self.execute_update(query, (start_date, end_date))
        logger.info(f"✓ 删除 {count} 条记录从 {self.TABLE_NAME}")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'name': row[2],
            'close': float(row[3]) if row[3] is not None else None,
            'p_change': float(row[4]) if row[4] is not None else None,
            'rank': row[5],
            'market_type': row[6],
            'amount': float(row[7]) if row[7] is not None else None,
            'net_amount': float(row[8]) if row[8] is not None else None,
            'sh_amount': float(row[9]) if row[9] is not None else None,
            'sh_net_amount': float(row[10]) if row[10] is not None else None,
            'sh_buy': float(row[11]) if row[11] is not None else None,
            'sh_sell': float(row[12]) if row[12] is not None else None,
            'sz_amount': float(row[13]) if row[13] is not None else None,
            'sz_net_amount': float(row[14]) if row[14] is not None else None,
            'sz_buy': float(row[15]) if row[15] is not None else None,
            'sz_sell': float(row[16]) if row[16] is not None else None
        }

    def get_top_by_net_amount(
        self,
        trade_date: str,
        limit: int = 20,
        market_type: Optional[str] = None
    ) -> List[Dict]:
        """
        获取指定日期净买入金额排名前N的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数
            market_type: 市场类型（可选）

        Returns:
            排名数据列表

        Examples:
            >>> repo = GgtTop10Repository()
            >>> top20 = repo.get_top_by_net_amount('20240115', limit=20)
        """
        conditions = ["trade_date = %s"]
        params = [trade_date]

        if market_type:
            conditions.append("market_type = %s")
            params.append(market_type)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        query = f"""
            SELECT
                trade_date,
                ts_code,
                name,
                close,
                p_change,
                rank,
                market_type,
                amount,
                net_amount,
                sh_amount,
                sh_net_amount,
                sh_buy,
                sh_sell,
                sz_amount,
                sz_net_amount,
                sz_buy,
                sz_sell
            FROM {self.TABLE_NAME}
            {where_clause}
            ORDER BY net_amount DESC
            LIMIT {limit}
        """

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]
