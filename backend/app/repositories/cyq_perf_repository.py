"""
每日筹码及胜率数据 Repository

管理 cyq_perf 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class CyqPerfRepository(BaseRepository):
    """每日筹码及胜率数据仓库"""

    TABLE_NAME = "cyq_perf"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CyqPerfRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询筹码及胜率数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = CyqPerfRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='600000.SH')
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

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    ts_code, trade_date, his_low, his_high,
                    cost_5pct, cost_15pct, cost_50pct, cost_85pct, cost_95pct,
                    weight_avg, winner_rate,
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
                    'his_low': float(row[2]) if row[2] is not None else None,
                    'his_high': float(row[3]) if row[3] is not None else None,
                    'cost_5pct': float(row[4]) if row[4] is not None else None,
                    'cost_15pct': float(row[5]) if row[5] is not None else None,
                    'cost_50pct': float(row[6]) if row[6] is not None else None,
                    'cost_85pct': float(row[7]) if row[7] is not None else None,
                    'cost_95pct': float(row[8]) if row[8] is not None else None,
                    'weight_avg': float(row[9]) if row[9] is not None else None,
                    'winner_rate': float(row[10]) if row[10] is not None else None,
                    'created_at': row[11].isoformat() + 'Z' if row[11] else None,
                    'updated_at': row[12].isoformat() + 'Z' if row[12] else None
                })

            logger.debug(f"查询到 {len(data)} 条筹码及胜率数据")
            return data

        except Exception as e:
            logger.error(f"查询筹码及胜率数据失败: {e}")
            raise QueryError(
                "数据查询失败",
                error_code="CYQ_PERF_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取筹码及胜率数据统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = CyqPerfRepository()
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

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(weight_avg) as avg_cost,
                    AVG(winner_rate) as avg_winner_rate,
                    MAX(winner_rate) as max_winner_rate,
                    MIN(winner_rate) as min_winner_rate
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            row = result[0] if result else None

            if row:
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'avg_cost': float(row[2]) if row[2] is not None else 0,
                    'avg_winner_rate': float(row[3]) if row[3] is not None else 0,
                    'max_winner_rate': float(row[4]) if row[4] is not None else 0,
                    'min_winner_rate': float(row[5]) if row[5] is not None else 0
                }
            else:
                return {
                    'total_count': 0,
                    'stock_count': 0,
                    'avg_cost': 0,
                    'avg_winner_rate': 0,
                    'max_winner_rate': 0,
                    'min_winner_rate': 0
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "统计信息查询失败",
                error_code="CYQ_PERF_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期（YYYYMMDD），如果没有数据返回 None

        Examples:
            >>> repo = CyqPerfRepository()
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
        批量插入/更新筹码及胜率数据（UPSERT）

        Args:
            df: 包含筹码及胜率数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = CyqPerfRepository()
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
                    to_python_type(row.get('his_low')),
                    to_python_type(row.get('his_high')),
                    to_python_type(row.get('cost_5pct')),
                    to_python_type(row.get('cost_15pct')),
                    to_python_type(row.get('cost_50pct')),
                    to_python_type(row.get('cost_85pct')),
                    to_python_type(row.get('cost_95pct')),
                    to_python_type(row.get('weight_avg')),
                    to_python_type(row.get('winner_rate'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, trade_date, his_low, his_high,
                    cost_5pct, cost_15pct, cost_50pct, cost_85pct, cost_95pct,
                    weight_avg, winner_rate,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (ts_code, trade_date)
                DO UPDATE SET
                    his_low = EXCLUDED.his_low,
                    his_high = EXCLUDED.his_high,
                    cost_5pct = EXCLUDED.cost_5pct,
                    cost_15pct = EXCLUDED.cost_15pct,
                    cost_50pct = EXCLUDED.cost_50pct,
                    cost_85pct = EXCLUDED.cost_85pct,
                    cost_95pct = EXCLUDED.cost_95pct,
                    weight_avg = EXCLUDED.weight_avg,
                    winner_rate = EXCLUDED.winner_rate,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条筹码及胜率数据")
            return count

        except Exception as e:
            logger.error(f"批量插入筹码及胜率数据失败: {e}")
            raise QueryError(
                "批量插入数据失败",
                error_code="CYQ_PERF_UPSERT_FAILED",
                reason=str(e)
            )

    def get_by_stock(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        获取指定股票的筹码及胜率数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = CyqPerfRepository()
            >>> data = repo.get_by_stock('600000.SH', limit=50)
        """
        return self.get_by_date_range(
            ts_code=ts_code,
            limit=limit
        )

    def get_top_winner_stocks(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期胜率最高的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            数据列表（按胜率排序）

        Examples:
            >>> repo = CyqPerfRepository()
            >>> data = repo.get_top_winner_stocks('20240115', limit=20)
        """
        try:
            query = f"""
                SELECT
                    ts_code, trade_date, his_low, his_high,
                    cost_5pct, cost_15pct, cost_50pct, cost_85pct, cost_95pct,
                    weight_avg, winner_rate
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY winner_rate DESC
                LIMIT %s
            """

            result = self.execute_query(query, (trade_date, limit))

            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'trade_date': row[1],
                    'his_low': float(row[2]) if row[2] is not None else None,
                    'his_high': float(row[3]) if row[3] is not None else None,
                    'cost_5pct': float(row[4]) if row[4] is not None else None,
                    'cost_15pct': float(row[5]) if row[5] is not None else None,
                    'cost_50pct': float(row[6]) if row[6] is not None else None,
                    'cost_85pct': float(row[7]) if row[7] is not None else None,
                    'cost_95pct': float(row[8]) if row[8] is not None else None,
                    'weight_avg': float(row[9]) if row[9] is not None else None,
                    'winner_rate': float(row[10]) if row[10] is not None else None
                })

            logger.debug(f"查询到 {len(data)} 个高胜率股票")
            return data

        except Exception as e:
            logger.error(f"查询高胜率股票失败: {e}")
            raise QueryError(
                "查询高胜率股票失败",
                error_code="CYQ_PERF_TOP_WINNER_FAILED",
                reason=str(e)
            )
