"""
最强板块统计 Repository
"""
from typing import List, Dict, Optional
import pandas as pd
from app.repositories.base_repository import BaseRepository
from loguru import logger


class LimitCptRepository(BaseRepository):
    """最强板块统计数据访问层"""

    TABLE_NAME = "limit_cpt_list"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ LimitCptRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询最强板块统计数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 板块代码（可选）
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = LimitCptRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240115', ts_code='885728.TI')
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
            limit_clause = f"LIMIT {limit}" if limit else ""

            query = f"""
                SELECT
                    trade_date, ts_code, name, days, up_stat,
                    cons_nums, up_nums, pct_chg, rank
                FROM {self.TABLE_NAME}
                {where_clause}
                ORDER BY trade_date DESC, rank ASC
                {limit_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询最强板块统计数据失败: {e}")
            raise

    def get_by_trade_date(self, trade_date: str, limit: Optional[int] = None) -> List[Dict]:
        """
        按交易日期查询最强板块统计数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = LimitCptRepository()
            >>> data = repo.get_by_trade_date('20240115', limit=20)
        """
        return self.get_by_date_range(
            start_date=trade_date,
            end_date=trade_date,
            limit=limit
        )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = LimitCptRepository()
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
                    COUNT(DISTINCT trade_date) as trading_days,
                    COUNT(DISTINCT ts_code) as concept_count,
                    AVG(up_nums) as avg_up_nums,
                    MAX(up_nums) as max_up_nums,
                    AVG(cons_nums) as avg_cons_nums,
                    MAX(cons_nums) as max_cons_nums,
                    AVG(pct_chg) as avg_pct_chg,
                    MAX(pct_chg) as max_pct_chg
                FROM {self.TABLE_NAME}
                {where_clause}
            """

            result = self.execute_query(query, tuple(params) if params else None)
            if result:
                row = result[0]
                return {
                    'trading_days': int(row[0]) if row[0] else 0,
                    'concept_count': int(row[1]) if row[1] else 0,
                    'avg_up_nums': float(row[2]) if row[2] else 0.0,
                    'max_up_nums': int(row[3]) if row[3] else 0,
                    'avg_cons_nums': float(row[4]) if row[4] else 0.0,
                    'max_cons_nums': int(row[5]) if row[5] else 0,
                    'avg_pct_chg': float(row[6]) if row[6] else 0.0,
                    'max_pct_chg': float(row[7]) if row[7] else 0.0
                }
            return {}

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新的交易日期

        Returns:
            最新交易日期，格式：YYYYMMDD

        Examples:
            >>> repo = LimitCptRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        try:
            query = f"""
                SELECT MAX(trade_date) as latest_date
                FROM {self.TABLE_NAME}
            """
            result = self.execute_query(query)
            return result[0][0] if result and result[0][0] else None

        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise

    def get_top_by_up_nums(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取涨停家数排名TOP数据

        Args:
            trade_date: 交易日期，格式：YYYYMMDD（可选，默认最新交易日）
            limit: 返回记录数

        Returns:
            排名TOP数据列表

        Examples:
            >>> repo = LimitCptRepository()
            >>> top_data = repo.get_top_by_up_nums('20240115', limit=20)
        """
        try:
            if not trade_date:
                trade_date = self.get_latest_trade_date()
                if not trade_date:
                    return []

            query = f"""
                SELECT
                    trade_date, ts_code, name, days, up_stat,
                    cons_nums, up_nums, pct_chg, rank
                FROM {self.TABLE_NAME}
                WHERE trade_date = %s
                ORDER BY up_nums DESC, rank ASC
                LIMIT %s
            """

            result = self.execute_query(query, (trade_date, limit))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"获取涨停家数排名失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新数据（UPSERT语义）

        Args:
            df: 包含数据的DataFrame

        Returns:
            影响的记录数

        Examples:
            >>> repo = LimitCptRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
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

            # UPSERT查询
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (trade_date, ts_code, name, days, up_stat, cons_nums, up_nums, pct_chg, rank, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (trade_date, ts_code)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    days = EXCLUDED.days,
                    up_stat = EXCLUDED.up_stat,
                    cons_nums = EXCLUDED.cons_nums,
                    up_nums = EXCLUDED.up_nums,
                    pct_chg = EXCLUDED.pct_chg,
                    rank = EXCLUDED.rank,
                    updated_at = NOW()
            """

            # 准备数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('trade_date')),
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('days')),
                    to_python_type(row.get('up_stat')),
                    to_python_type(row.get('cons_nums')),
                    to_python_type(row.get('up_nums')),
                    to_python_type(row.get('pct_chg')),
                    to_python_type(row.get('rank'))
                ))

            # 批量执行
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条最强板块统计数据")
            return count

        except Exception as e:
            logger.error(f"批量插入/更新数据失败: {e}")
            raise

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
            >>> repo = LimitCptRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE trade_date >= %s AND trade_date <= %s
            """
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除了 {count} 条数据")
            return count

        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'name': row[2],
            'days': row[3],
            'up_stat': row[4],
            'cons_nums': row[5],
            'up_nums': row[6],
            'pct_chg': float(row[7]) if row[7] is not None else None,
            'rank': row[8]
        }
