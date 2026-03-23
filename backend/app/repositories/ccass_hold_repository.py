"""
中央结算系统持股汇总 Repository

管理 ccass_hold 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class CcassHoldRepository(BaseRepository):
    """中央结算系统持股汇总仓库"""

    TABLE_NAME = "ccass_hold"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CcassHoldRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询中央结算系统持股汇总数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码，如 '605009.SH'（可选）
            hk_code: 港交所代码，如 '95009'（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = CcassHoldRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='605009.SH')
            >>> data = repo.get_by_date_range('20240101', '20240131', hk_code='95009')
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

            if hk_code:
                conditions.append("hk_code = %s")
                params.append(hk_code)

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    trade_date, ts_code, hk_code, name,
                    shareholding, hold_nums, hold_ratio,
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
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "hk_code": row[2],
                    "name": row[3],
                    "shareholding": row[4],
                    "hold_nums": row[5],
                    "hold_ratio": float(row[6]) if row[6] is not None else None,
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None,
                })

            return data

        except Exception as e:
            logger.error(f"查询中央结算系统持股汇总数据失败: {e}")
            raise QueryError(
                "查询中央结算系统持股汇总数据失败",
                error_code="CCASS_HOLD_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取中央结算系统持股汇总统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计数据字典

        Examples:
            >>> repo = CcassHoldRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
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

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(shareholding) as avg_shareholding,
                    MAX(shareholding) as max_shareholding,
                    AVG(hold_nums) as avg_hold_nums,
                    AVG(hold_ratio) as avg_hold_ratio,
                    MAX(hold_ratio) as max_hold_ratio
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    "total_count": row[0] or 0,
                    "stock_count": row[1] or 0,
                    "avg_shareholding": int(row[2]) if row[2] is not None else 0,
                    "max_shareholding": row[3] or 0,
                    "avg_hold_nums": int(row[4]) if row[4] is not None else 0,
                    "avg_hold_ratio": float(row[5]) if row[5] is not None else 0.0,
                    "max_hold_ratio": float(row[6]) if row[6] is not None else 0.0,
                }
            else:
                return {
                    "total_count": 0,
                    "stock_count": 0,
                    "avg_shareholding": 0,
                    "max_shareholding": 0,
                    "avg_hold_nums": 0,
                    "avg_hold_ratio": 0.0,
                    "max_hold_ratio": 0.0,
                }

        except Exception as e:
            logger.error(f"获取中央结算系统持股汇总统计数据失败: {e}")
            raise QueryError(
                "获取中央结算系统持股汇总统计数据失败",
                error_code="CCASS_HOLD_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_trade_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新交易日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新交易日期（YYYYMMDD格式）

        Examples:
            >>> repo = CcassHoldRepository()
            >>> latest_date = repo.get_latest_trade_date()
            >>> latest_date = repo.get_latest_trade_date(ts_code='605009.SH')
        """
        try:
            conditions = []
            params = []

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT MAX(trade_date)
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0 and result[0][0]:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise QueryError(
                "获取最新交易日期失败",
                error_code="CCASS_HOLD_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新中央结算系统持股汇总数据

        Args:
            df: 包含中央结算系统持股汇总数据的 DataFrame

        Returns:
            影响的记录数

        Examples:
            >>> repo = CcassHoldRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
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
                    to_python_type(row.get('hk_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('shareholding')),
                    to_python_type(row.get('hold_nums')),
                    to_python_type(row.get('hold_ratio')),
                ))

            # 批量插入（UPSERT）
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, ts_code, hk_code, name, shareholding, hold_nums, hold_ratio, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    hk_code = EXCLUDED.hk_code,
                    name = EXCLUDED.name,
                    shareholding = EXCLUDED.shareholding,
                    hold_nums = EXCLUDED.hold_nums,
                    hold_ratio = EXCLUDED.hold_ratio,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条中央结算系统持股汇总数据")
            return count

        except Exception as e:
            logger.error(f"批量插入中央结算系统持股汇总数据失败: {e}")
            raise QueryError(
                "批量插入中央结算系统持股汇总数据失败",
                error_code="CCASS_HOLD_BULK_INSERT_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, trade_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定交易日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            是否存在

        Examples:
            >>> repo = CcassHoldRepository()
            >>> exists = repo.exists_by_date('20240115')
            >>> exists = repo.exists_by_date('20240115', ts_code='605009.SH')
        """
        try:
            conditions = ["trade_date = %s"]
            params = [trade_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT COUNT(*)
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            return result and len(result) > 0 and result[0][0] > 0

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
            ts_code: 股票代码（可选）

        Returns:
            记录数

        Examples:
            >>> repo = CcassHoldRepository()
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

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

            query = f"""
                SELECT COUNT(*)
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            return result[0][0] if result and len(result) > 0 else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            return 0

    def get_top_by_shareholding(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期持股量排名前N的股票

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            排名数据列表

        Examples:
            >>> repo = CcassHoldRepository()
            >>> top20 = repo.get_top_by_shareholding('20240115', limit=20)
        """
        try:
            query = f"""
                SELECT
                    trade_date, ts_code, hk_code, name,
                    shareholding, hold_nums, hold_ratio
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY shareholding DESC
                LIMIT %s
            """

            result = self.execute_query(query, (trade_date, limit))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    "trade_date": row[0],
                    "ts_code": row[1],
                    "hk_code": row[2],
                    "name": row[3],
                    "shareholding": row[4],
                    "hold_nums": row[5],
                    "hold_ratio": float(row[6]) if row[6] is not None else None,
                })

            return data

        except Exception as e:
            logger.error(f"获取持股量排名失败: {e}")
            raise QueryError(
                "获取持股量排名失败",
                error_code="CCASS_HOLD_TOP_FAILED",
                reason=str(e)
            )
