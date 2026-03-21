"""
龙虎榜机构明细 Repository
"""
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class TopInstRepository(BaseRepository):
    """龙虎榜机构明细 Repository"""

    TABLE_NAME = "top_inst"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ TopInstRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        side: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询龙虎榜机构明细

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            side: 买卖类型（可选，0：买入，1：卖出）
            limit: 返回记录数限制（可选）

        Returns:
            龙虎榜机构明细列表

        Examples:
            >>> repo = TopInstRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data_with_code = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        conditions = ["trade_date >= %s", "trade_date <= %s"]
        params = [start_date, end_date]

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        if side is not None:
            conditions.append("side = %s")
            params.append(side)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT trade_date, ts_code, exalter, side, buy, buy_rate,
                   sell, sell_rate, net_buy, reason
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY trade_date DESC, ABS(net_buy) DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        try:
            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询龙虎榜机构明细失败: {e}")
            raise QueryError(
                "查询龙虎榜机构明细失败",
                error_code="TOP_INST_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_trade_date(self, trade_date: str, ts_code: Optional[str] = None) -> List[Dict]:
        """
        按单个交易日期查询龙虎榜机构明细

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            龙虎榜机构明细列表
        """
        conditions = ["trade_date = %s"]
        params = [trade_date]

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT trade_date, ts_code, exalter, side, buy, buy_rate,
                   sell, sell_rate, net_buy, reason
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
            ORDER BY ABS(net_buy) DESC
        """

        try:
            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询龙虎榜机构明细失败: {e}")
            raise QueryError(
                "查询龙虎榜机构明细失败",
                error_code="TOP_INST_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取龙虎榜机构明细统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = TopInstRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        conditions = ["trade_date >= %s", "trade_date <= %s"]
        params = [start_date, end_date]

        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT trade_date) as trading_days,
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(DISTINCT exalter) as exalter_count,
                AVG(net_buy) as avg_net_buy,
                MAX(net_buy) as max_net_buy,
                MIN(net_buy) as min_net_buy,
                SUM(CASE WHEN net_buy > 0 THEN net_buy ELSE 0 END) as total_net_buy,
                SUM(CASE WHEN net_buy < 0 THEN net_buy ELSE 0 END) as total_net_sell
            FROM {self.TABLE_NAME}
            WHERE {where_clause}
        """

        try:
            result = self.execute_query(query, tuple(params))
            if result and len(result) > 0:
                row = result[0]
                return {
                    "total_records": int(row[0]) if row[0] else 0,
                    "trading_days": int(row[1]) if row[1] else 0,
                    "stock_count": int(row[2]) if row[2] else 0,
                    "exalter_count": int(row[3]) if row[3] else 0,
                    "avg_net_buy": float(row[4]) if row[4] else 0.0,
                    "max_net_buy": float(row[5]) if row[5] else 0.0,
                    "min_net_buy": float(row[6]) if row[6] else 0.0,
                    "total_net_buy": float(row[7]) if row[7] else 0.0,
                    "total_net_sell": float(row[8]) if row[8] else 0.0
                }
            return {
                "total_records": 0,
                "trading_days": 0,
                "stock_count": 0,
                "exalter_count": 0,
                "avg_net_buy": 0.0,
                "max_net_buy": 0.0,
                "min_net_buy": 0.0,
                "total_net_buy": 0.0,
                "total_net_sell": 0.0
            }
        except Exception as e:
            logger.error(f"查询龙虎榜机构明细统计失败: {e}")
            raise QueryError(
                "查询龙虎榜机构明细统计失败",
                error_code="TOP_INST_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式）或 None

        Examples:
            >>> repo = TopInstRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"

        try:
            result = self.execute_query(query, ())
            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            return None
        except Exception as e:
            logger.error(f"查询最新交易日期失败: {e}")
            raise QueryError(
                "查询最新交易日期失败",
                error_code="TOP_INST_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新龙虎榜机构明细数据

        Args:
            df: pandas DataFrame，包含龙虎榜机构明细数据

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = TopInstRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        # 数据验证和清洗
        required_columns = [
            'trade_date', 'ts_code', 'exalter', 'side',
            'buy', 'buy_rate', 'sell', 'sell_rate', 'net_buy', 'reason'
        ]

        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"缺少必需列: {col}")

        # 填充缺失值
        df = df.fillna({
            'buy': 0.0,
            'buy_rate': 0.0,
            'sell': 0.0,
            'sell_rate': 0.0,
            'net_buy': 0.0,
            'reason': ''
        })

        # UPSERT 语句
        upsert_query = f"""
            INSERT INTO {self.TABLE_NAME}
            (trade_date, ts_code, exalter, side, buy, buy_rate, sell, sell_rate, net_buy, reason, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (trade_date, ts_code, exalter, side)
            DO UPDATE SET
                buy = EXCLUDED.buy,
                buy_rate = EXCLUDED.buy_rate,
                sell = EXCLUDED.sell,
                sell_rate = EXCLUDED.sell_rate,
                net_buy = EXCLUDED.net_buy,
                reason = EXCLUDED.reason,
                updated_at = NOW()
        """

        # 准备批量插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                str(row['trade_date']),
                str(row['ts_code']),
                str(row['exalter']),
                str(row['side']),
                float(row['buy']) if pd.notna(row['buy']) else 0.0,
                float(row['buy_rate']) if pd.notna(row['buy_rate']) else 0.0,
                float(row['sell']) if pd.notna(row['sell']) else 0.0,
                float(row['sell_rate']) if pd.notna(row['sell_rate']) else 0.0,
                float(row['net_buy']) if pd.notna(row['net_buy']) else 0.0,
                str(row['reason']) if pd.notna(row['reason']) else ''
            ))

        try:
            count = self.execute_batch(upsert_query, values)
            logger.info(f"成功插入/更新 {count} 条龙虎榜机构明细数据")
            return count
        except Exception as e:
            logger.error(f"批量插入/更新龙虎榜机构明细数据失败: {e}")
            raise DatabaseError(
                "批量插入/更新龙虎榜机构明细数据失败",
                error_code="TOP_INST_UPSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        按日期范围删除龙虎榜机构明细数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数
        """
        query = f"DELETE FROM {self.TABLE_NAME} WHERE trade_date >= %s AND trade_date <= %s"

        try:
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"成功删除 {count} 条龙虎榜机构明细数据")
            return count
        except Exception as e:
            logger.error(f"删除龙虎榜机构明细数据失败: {e}")
            raise DatabaseError(
                "删除龙虎榜机构明细数据失败",
                error_code="TOP_INST_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的龙虎榜机构明细数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            True 如果数据存在，否则 False
        """
        query = f"SELECT EXISTS(SELECT 1 FROM {self.TABLE_NAME} WHERE trade_date = %s)"

        try:
            result = self.execute_query(query, (trade_date,))
            return result[0][0] if result else False
        except Exception as e:
            logger.error(f"检查龙虎榜机构明细数据是否存在失败: {e}")
            return False

    def get_record_count(self, start_date: str, end_date: str) -> int:
        """
        获取指定日期范围内的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date >= %s AND trade_date <= %s"

        try:
            result = self.execute_query(query, (start_date, end_date))
            return int(result[0][0]) if result else 0
        except Exception as e:
            logger.error(f"获取龙虎榜机构明细记录数失败: {e}")
            return 0

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            "trade_date": row[0],
            "ts_code": row[1],
            "exalter": row[2],
            "side": row[3],
            "buy": float(row[4]) if row[4] is not None else 0.0,
            "buy_rate": float(row[5]) if row[5] is not None else 0.0,
            "sell": float(row[6]) if row[6] is not None else 0.0,
            "sell_rate": float(row[7]) if row[7] is not None else 0.0,
            "net_buy": float(row[8]) if row[8] is not None else 0.0,
            "reason": row[9] if row[9] else ""
        }
