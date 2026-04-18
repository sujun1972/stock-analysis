"""
实时行情数据 Repository

负责 stock_realtime 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class StockRealtimeRepository(BaseRepository):
    """实时行情数据 Repository"""

    TABLE_NAME = "stock_realtime"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StockRealtimeRepository initialized")

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        获取所有实时行情数据（支持分页）

        Args:
            limit: 限制返回记录数
            offset: 偏移量（用于分页）

        Returns:
            实时行情数据列表
        """
        try:
            query = f"""
                SELECT code, name, latest_price, open, high, low, pre_close,
                       volume, amount, pct_change, change_amount, turnover, amplitude,
                       trade_time, data_source, updated_at
                FROM {self.TABLE_NAME}
                ORDER BY pct_change DESC
            """

            params = []
            query += " LIMIT %s"
            params.append(self._enforce_limit(limit))
            if offset:
                query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except PsycopgDatabaseError as e:
            logger.error(f"查询实时行情数据失败: {e}")
            raise QueryError(
                "查询实时行情数据失败",
                error_code="REALTIME_QUERY_FAILED",
                reason=str(e)
            )

    def count_all(self) -> int:
        """
        获取所有实时行情数据的总数

        Returns:
            记录总数
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME}"
            result = self.execute_query(query)
            return int(result[0][0]) if result else 0

        except PsycopgDatabaseError as e:
            logger.error(f"查询实时行情数据总数失败: {e}")
            raise QueryError(
                "查询实时行情数据总数失败",
                error_code="REALTIME_COUNT_FAILED",
                reason=str(e)
            )

    def get_by_code(self, code: str) -> Optional[Dict]:
        """
        根据股票代码查询实时行情

        Args:
            code: 股票代码

        Returns:
            实时行情数据字典，不存在返回None
        """
        try:
            query = f"""
                SELECT code, name, latest_price, open, high, low, pre_close,
                       volume, amount, pct_change, change_amount, turnover, amplitude,
                       trade_time, data_source, updated_at
                FROM {self.TABLE_NAME}
                WHERE code = %s
            """

            result = self.execute_query(query, (code,))
            return self._row_to_dict(result[0]) if result else None

        except PsycopgDatabaseError as e:
            logger.error(f"查询股票 {code} 实时行情失败: {e}")
            raise QueryError(
                f"查询股票 {code} 实时行情失败",
                error_code="REALTIME_QUERY_BY_CODE_FAILED",
                reason=str(e)
            )

    def get_top_gainers(self, limit: int = 50) -> List[Dict]:
        """
        获取涨幅榜前N名

        Args:
            limit: 返回记录数

        Returns:
            涨幅榜数据列表
        """
        try:
            query = f"""
                SELECT code, name, latest_price, open, high, low, pre_close,
                       volume, amount, pct_change, change_amount, turnover, amplitude,
                       trade_time, data_source, updated_at
                FROM {self.TABLE_NAME}
                WHERE pct_change IS NOT NULL
                ORDER BY pct_change DESC
                LIMIT %s
            """

            result = self.execute_query(query, (limit,))
            return [self._row_to_dict(row) for row in result]

        except PsycopgDatabaseError as e:
            logger.error(f"查询涨幅榜失败: {e}")
            raise QueryError(
                "查询涨幅榜失败",
                error_code="REALTIME_TOP_GAINERS_FAILED",
                reason=str(e)
            )

    def get_top_losers(self, limit: int = 50) -> List[Dict]:
        """
        获取跌幅榜前N名

        Args:
            limit: 返回记录数

        Returns:
            跌幅榜数据列表
        """
        try:
            query = f"""
                SELECT code, name, latest_price, open, high, low, pre_close,
                       volume, amount, pct_change, change_amount, turnover, amplitude,
                       trade_time, data_source, updated_at
                FROM {self.TABLE_NAME}
                WHERE pct_change IS NOT NULL
                ORDER BY pct_change ASC
                LIMIT %s
            """

            result = self.execute_query(query, (limit,))
            return [self._row_to_dict(row) for row in result]

        except PsycopgDatabaseError as e:
            logger.error(f"查询跌幅榜失败: {e}")
            raise QueryError(
                "查询跌幅榜失败",
                error_code="REALTIME_TOP_LOSERS_FAILED",
                reason=str(e)
            )

    def get_statistics(self) -> Dict:
        """
        获取实时行情统计信息

        Returns:
            统计信息字典
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN pct_change > 0 THEN 1 END) as rising_count,
                    COUNT(CASE WHEN pct_change < 0 THEN 1 END) as falling_count,
                    COUNT(CASE WHEN pct_change = 0 THEN 1 END) as unchanged_count,
                    AVG(pct_change) as avg_pct_change,
                    MAX(pct_change) as max_pct_change,
                    MIN(pct_change) as min_pct_change,
                    SUM(volume) as total_volume,
                    SUM(amount) as total_amount,
                    MAX(updated_at) as last_updated
                FROM {self.TABLE_NAME}
            """

            result = self.execute_query(query)
            if result:
                row = result[0]
                return {
                    'total_count': int(row[0]) if row[0] is not None else 0,
                    'rising_count': int(row[1]) if row[1] is not None else 0,
                    'falling_count': int(row[2]) if row[2] is not None else 0,
                    'unchanged_count': int(row[3]) if row[3] is not None else 0,
                    'avg_pct_change': float(row[4]) if row[4] is not None else 0.0,
                    'max_pct_change': float(row[5]) if row[5] is not None else 0.0,
                    'min_pct_change': float(row[6]) if row[6] is not None else 0.0,
                    'total_volume': int(row[7]) if row[7] is not None else 0,
                    'total_amount': float(row[8]) if row[8] is not None else 0.0,
                    'last_updated': row[9].isoformat() if row[9] is not None else None
                }
            return {}

        except PsycopgDatabaseError as e:
            logger.error(f"查询实时行情统计信息失败: {e}")
            raise QueryError(
                "查询实时行情统计信息失败",
                error_code="REALTIME_STATISTICS_FAILED",
                reason=str(e)
            )

    def get_last_updated(self, codes: Optional[List[str]] = None) -> Optional[object]:
        """
        获取实时行情最后更新时间

        Args:
            codes: 股票代码列表（可选，不指定则查全表）

        Returns:
            最后更新时间（datetime 对象），无数据时返回 None
        """
        try:
            if codes:
                placeholders = ','.join(['%s'] * len(codes))
                query = f"SELECT MAX(updated_at) FROM {self.TABLE_NAME} WHERE code IN ({placeholders})"
                result = self.execute_query(query, tuple(codes))
            else:
                query = f"SELECT MAX(updated_at) FROM {self.TABLE_NAME}"
                result = self.execute_query(query)
            if result and result[0][0] is not None:
                return result[0][0]
            return None
        except Exception as e:
            logger.warning(f"获取实时行情最后更新时间失败: {e}")
            return None

    def delete_all(self) -> int:
        """
        清空实时行情表（用于重新同步）

        Returns:
            删除的记录数
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME}"
            count = self.execute_update(query)
            logger.info(f"已清空实时行情表，删除 {count} 条记录")
            return count

        except PsycopgDatabaseError as e:
            logger.error(f"清空实时行情表失败: {e}")
            raise QueryError(
                "清空实时行情表失败",
                error_code="REALTIME_DELETE_ALL_FAILED",
                reason=str(e)
            )

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'code': row[0],
            'name': row[1],
            'latest_price': float(row[2]) if row[2] is not None else None,
            'open': float(row[3]) if row[3] is not None else None,
            'high': float(row[4]) if row[4] is not None else None,
            'low': float(row[5]) if row[5] is not None else None,
            'pre_close': float(row[6]) if row[6] is not None else None,
            'volume': int(row[7]) if row[7] is not None else None,
            'amount': float(row[8]) if row[8] is not None else None,
            'pct_change': float(row[9]) if row[9] is not None else None,
            'change_amount': float(row[10]) if row[10] is not None else None,
            'turnover': float(row[11]) if row[11] is not None else None,
            'amplitude': float(row[12]) if row[12] is not None else None,
            'trade_time': row[13].isoformat() if row[13] is not None else None,
            'data_source': row[14],
            'updated_at': row[15].isoformat() if row[15] is not None else None
        }
