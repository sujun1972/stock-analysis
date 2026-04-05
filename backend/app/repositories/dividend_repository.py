"""
分红送股数据 Repository

提供分红送股数据的数据库访问操作
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class DividendRepository(BaseRepository):
    """分红送股数据 Repository"""

    TABLE_NAME = "dividend"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ DividendRepository initialized")

    def get_by_ts_code(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码查询分红送股数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期，格式：YYYYMMDD（基于ann_date）
            end_date: 结束日期，格式：YYYYMMDD（基于ann_date）
            limit: 返回记录数限制

        Returns:
            分红送股数据列表

        Examples:
            >>> repo = DividendRepository()
            >>> data = repo.get_by_ts_code('600848.SH', '20200101', '20241231')
        """
        query = f"""
            SELECT ts_code, end_date, ann_date, div_proc, stk_div, stk_bo_rate,
                   stk_co_rate, cash_div, cash_div_tax, record_date, ex_date,
                   pay_date, div_listdate, imp_ann_date, base_date, base_share
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
        """
        params = [ts_code]

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)

        query += " ORDER BY ann_date DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> int:
        """获取符合条件的记录总数"""
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
            params = []
            if start_date:
                query += " AND ann_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND ann_date <= %s"
                params.append(end_date)
            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)
            result = self.execute_query(query, tuple(params) if params else None)
            return int(result[0][0]) if result else 0
        except Exception as e:
            logger.error(f"获取分红送股记录总数失败: {e}")
            raise

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询分红送股数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD（基于ann_date）
            end_date: 结束日期，格式：YYYYMMDD（基于ann_date）
            ts_code: 股票代码（可选）
            limit: 返回记录数限制
            offset: 偏移量（用于分页）

        Returns:
            分红送股数据列表

        Examples:
            >>> repo = DividendRepository()
            >>> data = repo.get_by_date_range('20200101', '20241231', limit=30, offset=0)
        """
        query = f"""
            SELECT ts_code, end_date, ann_date, div_proc, stk_div, stk_bo_rate,
                   stk_co_rate, cash_div, cash_div_tax, record_date, ex_date,
                   pay_date, div_listdate, imp_ann_date, base_date, base_share
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)
        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY ann_date DESC"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        if offset:
            query += " OFFSET %s"
            params.append(offset)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取分红送股统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = DividendRepository()
            >>> stats = repo.get_statistics('20200101', '20241231')
        """
        query = f"""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ts_code) as stock_count,
                AVG(CASE WHEN cash_div IS NOT NULL THEN cash_div ELSE 0 END) as avg_cash_div,
                MAX(CASE WHEN cash_div IS NOT NULL THEN cash_div ELSE 0 END) as max_cash_div,
                AVG(CASE WHEN stk_div IS NOT NULL THEN stk_div ELSE 0 END) as avg_stk_div,
                MAX(CASE WHEN stk_div IS NOT NULL THEN stk_div ELSE 0 END) as max_stk_div
            FROM {self.TABLE_NAME}
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND ann_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND ann_date <= %s"
            params.append(end_date)
        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        result = self.execute_query(query, tuple(params))
        if result:
            row = result[0]
            return {
                'total_records': int(row[0]) if row[0] else 0,
                'stock_count': int(row[1]) if row[1] else 0,
                'avg_cash_div': float(row[2]) if row[2] else 0.0,
                'max_cash_div': float(row[3]) if row[3] else 0.0,
                'avg_stk_div': float(row[4]) if row[4] else 0.0,
                'max_stk_div': float(row[5]) if row[5] else 0.0
            }
        return {
            'total_records': 0,
            'stock_count': 0,
            'avg_cash_div': 0.0,
            'max_cash_div': 0.0,
            'avg_stk_div': 0.0,
            'max_stk_div': 0.0
        }

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新分红送股数据

        Args:
            df: 包含分红送股数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = DividendRepository()
            >>> import pandas as pd
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

        # UPSERT 查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, end_date, ann_date, div_proc, stk_div, stk_bo_rate, stk_co_rate,
             cash_div, cash_div_tax, record_date, ex_date, pay_date, div_listdate,
             imp_ann_date, base_date, base_share, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (ts_code, end_date, ann_date)
            DO UPDATE SET
                div_proc = EXCLUDED.div_proc,
                stk_div = EXCLUDED.stk_div,
                stk_bo_rate = EXCLUDED.stk_bo_rate,
                stk_co_rate = EXCLUDED.stk_co_rate,
                cash_div = EXCLUDED.cash_div,
                cash_div_tax = EXCLUDED.cash_div_tax,
                record_date = EXCLUDED.record_date,
                ex_date = EXCLUDED.ex_date,
                pay_date = EXCLUDED.pay_date,
                div_listdate = EXCLUDED.div_listdate,
                imp_ann_date = EXCLUDED.imp_ann_date,
                base_date = EXCLUDED.base_date,
                base_share = EXCLUDED.base_share,
                updated_at = NOW()
        """

        # 准备插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('end_date')),
                to_python_type(row.get('ann_date')),
                to_python_type(row.get('div_proc')),
                to_python_type(row.get('stk_div')),
                to_python_type(row.get('stk_bo_rate')),
                to_python_type(row.get('stk_co_rate')),
                to_python_type(row.get('cash_div')),
                to_python_type(row.get('cash_div_tax')),
                to_python_type(row.get('record_date')),
                to_python_type(row.get('ex_date')),
                to_python_type(row.get('pay_date')),
                to_python_type(row.get('div_listdate')),
                to_python_type(row.get('imp_ann_date')),
                to_python_type(row.get('base_date')),
                to_python_type(row.get('base_share')),
            ))

        # 执行批量插入
        count = self.execute_batch(query, values)
        logger.info(f"✓ 批量插入/更新 {count} 条分红送股数据")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        if not row:
            return {}

        return {
            'ts_code': row[0],
            'end_date': row[1],
            'ann_date': row[2],
            'div_proc': row[3],
            'stk_div': float(row[4]) if row[4] is not None else None,
            'stk_bo_rate': float(row[5]) if row[5] is not None else None,
            'stk_co_rate': float(row[6]) if row[6] is not None else None,
            'cash_div': float(row[7]) if row[7] is not None else None,
            'cash_div_tax': float(row[8]) if row[8] is not None else None,
            'record_date': row[9],
            'ex_date': row[10],
            'pay_date': row[11],
            'div_listdate': row[12],
            'imp_ann_date': row[13],
            'base_date': row[14],
            'base_share': float(row[15]) if row[15] is not None else None
        }
