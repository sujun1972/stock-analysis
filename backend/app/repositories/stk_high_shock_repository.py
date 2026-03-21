"""
个股严重异常波动 Repository

管理 stk_high_shock 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class StkHighShockRepository(BaseRepository):
    """个股严重异常波动仓库"""

    TABLE_NAME = "stk_high_shock"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkHighShockRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_market: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询个股严重异常波动数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            trade_market: 交易所（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = StkHighShockRepository()
            >>> data = repo.get_by_date_range('20260301', '20260331')
            >>> data = repo.get_by_date_range('20260301', '20260331', ts_code='000001.SZ')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("trade_date >= %s")
                params.append(start_date)
            else:
                conditions.append("trade_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("trade_date <= %s")
                params.append(end_date)
            else:
                conditions.append("trade_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if trade_market:
                conditions.append("trade_market = %s")
                params.append(trade_market)

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    ts_code, trade_date, name, trade_market, reason, period,
                    created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY trade_date DESC, ts_code
            """

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'trade_date': row[1],
                    'name': row[2],
                    'trade_market': row[3],
                    'reason': row[4],
                    'period': row[5],
                    'created_at': row[6].isoformat() + 'Z' if row[6] else None,
                    'updated_at': row[7].isoformat() + 'Z' if row[7] else None
                })

            logger.debug(f"查询到 {len(data)} 条个股严重异常波动数据")
            return data

        except Exception as e:
            logger.error(f"查询个股严重异常波动数据失败: {e}")
            raise QueryError(
                "数据查询失败",
                error_code="STK_HIGH_SHOCK_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取个股严重异常波动统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkHighShockRepository()
            >>> stats = repo.get_statistics('20260301', '20260331')
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

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(DISTINCT trade_market) as market_count
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            row = result[0] if result else None

            if row:
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'market_count': int(row[2]) if row[2] else 0
                }
            else:
                return {
                    'total_count': 0,
                    'stock_count': 0,
                    'market_count': 0
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "统计信息查询失败",
                error_code="STK_HIGH_SHOCK_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYYMMDD），如果没有数据返回 None

        Examples:
            >>> repo = StkHighShockRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        try:
            query = f"""
                SELECT MAX(trade_date)
                FROM {self.TABLE_NAME}
            """

            result = self.execute_query(query, ())
            latest_date = result[0][0] if result and result[0][0] else None

            logger.debug(f"最新交易日期: {latest_date}")
            return latest_date

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新个股严重异常波动数据（UPSERT）

        Args:
            df: 包含个股严重异常波动数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkHighShockRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将 pandas/numpy 类型转换为 Python 原生类型
            def to_python_type(value):
                """
                将 pandas/numpy 类型转换为 Python 原生类型

                关键问题：psycopg2 无法直接处理 numpy 类型
                必须转换为 Python 原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换 numpy 整数类型为 Python int
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                # 转换 numpy 浮点类型为 Python float
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('trade_market')),
                    to_python_type(row.get('reason')),
                    to_python_type(row.get('period'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, trade_date, name, trade_market, reason, period,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (ts_code, trade_date)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    trade_market = EXCLUDED.trade_market,
                    reason = EXCLUDED.reason,
                    period = EXCLUDED.period,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条个股严重异常波动数据")
            return count

        except Exception as e:
            logger.error(f"批量插入个股严重异常波动数据失败: {e}")
            raise QueryError(
                "批量插入数据失败",
                error_code="STK_HIGH_SHOCK_UPSERT_FAILED",
                reason=str(e)
            )

    def get_by_stock(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        获取指定股票的个股严重异常波动数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = StkHighShockRepository()
            >>> data = repo.get_by_stock('000001.SZ', limit=50)
        """
        return self.get_by_date_range(
            ts_code=ts_code,
            limit=limit
        )

    def get_by_market(
        self,
        trade_market: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        按交易所查询个股严重异常波动数据

        Args:
            trade_market: 交易所
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 返回记录数限制

        Returns:
            数据列表（按trade_date降序排序）

        Examples:
            >>> repo = StkHighShockRepository()
            >>> data = repo.get_by_market('创业板', start_date='20260301', limit=50)
        """
        return self.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            trade_market=trade_market,
            limit=limit
        )
