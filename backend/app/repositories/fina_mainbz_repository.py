"""
主营业务构成数据 Repository

管理 fina_mainbz 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class FinaMainbzRepository(BaseRepository):
    """主营业务构成数据 Repository"""

    TABLE_NAME = "fina_mainbz"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ FinaMainbzRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询主营业务构成数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            type: 类型，P按产品 D按地区 I按行业（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, end_date, bz_item, bz_sales, bz_profit, bz_cost,
                   curr_type, update_flag
            FROM {self.TABLE_NAME}
            WHERE end_date >= %s AND end_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY end_date DESC, ts_code, bz_sales DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_period(
        self,
        period: str,
        ts_code: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期查询主营业务构成数据

        Args:
            period: 报告期，格式：YYYYMMDD（如20231231表示年报）
            ts_code: 股票代码（可选）
            type: 类型，P按产品 D按地区 I按行业（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, end_date, bz_item, bz_sales, bz_profit, bz_cost,
                   curr_type, update_flag
            FROM {self.TABLE_NAME}
            WHERE end_date = %s
        """
        params = [period]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY ts_code, bz_sales DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_code(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码查询主营业务构成数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            type: 类型，P按产品 D按地区 I按行业（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, end_date, bz_item, bz_sales, bz_profit, bz_cost,
                   curr_type, update_flag
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
        """
        params = [ts_code]

        if start_date:
            query += " AND end_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND end_date <= %s"
            params.append(end_date)

        query += " ORDER BY end_date DESC, bz_sales DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取主营业务构成统计信息

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            ts_code: 股票代码（可选）

        Returns:
            统计信息
        """
        query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT ts_code) as stock_count,
                COUNT(DISTINCT end_date) as period_count,
                COUNT(DISTINCT bz_item) as bz_item_count,
                AVG(bz_sales) as avg_bz_sales,
                SUM(bz_sales) as total_bz_sales,
                MAX(bz_sales) as max_bz_sales,
                MIN(bz_sales) as min_bz_sales
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND end_date >= %s"
            params.append(start_date)

        if end_date:
            query += " AND end_date <= %s"
            params.append(end_date)

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params) if params else None)
        if result:
            row = result[0]
            return {
                'total_count': row[0] or 0,
                'stock_count': row[1] or 0,
                'period_count': row[2] or 0,
                'bz_item_count': row[3] or 0,
                'avg_bz_sales': float(row[4]) if row[4] else 0.0,
                'total_bz_sales': float(row[5]) if row[5] else 0.0,
                'max_bz_sales': float(row[6]) if row[6] else 0.0,
                'min_bz_sales': float(row[7]) if row[7] else 0.0
            }
        return {}

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新主营业务构成数据（UPSERT）

        Args:
            df: 包含主营业务构成数据的 DataFrame

        Returns:
            插入/更新的记录数
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
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
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('end_date')),
                to_python_type(row.get('bz_item')),
                to_python_type(row.get('bz_sales')),
                to_python_type(row.get('bz_profit')),
                to_python_type(row.get('bz_cost')),
                to_python_type(row.get('curr_type')),
                to_python_type(row.get('update_flag'))
            ))

        # UPSERT查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, end_date, bz_item, bz_sales, bz_profit, bz_cost, curr_type, update_flag)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts_code, end_date, bz_item)
            DO UPDATE SET
                bz_sales = EXCLUDED.bz_sales,
                bz_profit = EXCLUDED.bz_profit,
                bz_cost = EXCLUDED.bz_cost,
                curr_type = EXCLUDED.curr_type,
                update_flag = EXCLUDED.update_flag,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"✓ 批量插入/更新 {count} 条主营业务构成数据")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'end_date': row[1],
            'bz_item': row[2],
            'bz_sales': float(row[3]) if row[3] is not None else None,
            'bz_profit': float(row[4]) if row[4] is not None else None,
            'bz_cost': float(row[5]) if row[5] is not None else None,
            'curr_type': row[6],
            'update_flag': row[7]
        }
