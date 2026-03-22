"""
财务指标数据 Repository

管理 fina_indicator 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class FinaIndicatorRepository(BaseRepository):
    """财务指标数据 Repository"""

    TABLE_NAME = "fina_indicator"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ FinaIndicatorRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询财务指标数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        # 查询核心财务指标（简化版，避免一次性查询150+字段）
        query = f"""
            SELECT ts_code, ann_date, end_date,
                   eps, dt_eps, bps, revenue_ps, capital_rese_ps,
                   roe, roe_waa, roe_dt, roa, roic,
                   debt_to_assets, assets_to_eqt, current_ratio, quick_ratio,
                   netprofit_margin, grossprofit_margin,
                   ar_turn, inv_turn, assets_turn,
                   basic_eps_yoy, netprofit_yoy, or_yoy, roe_yoy
            FROM {self.TABLE_NAME}
            WHERE ann_date >= %s AND ann_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        query += " ORDER BY ann_date DESC, ts_code"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_period(
        self,
        period: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期查询财务指标数据

        Args:
            period: 报告期，格式：YYYYMMDD（如20231231表示年报）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, ann_date, end_date,
                   eps, dt_eps, bps, revenue_ps, capital_rese_ps,
                   roe, roe_waa, roe_dt, roa, roic,
                   debt_to_assets, assets_to_eqt, current_ratio, quick_ratio,
                   netprofit_margin, grossprofit_margin,
                   ar_turn, inv_turn, assets_turn,
                   basic_eps_yoy, netprofit_yoy, or_yoy, roe_yoy
            FROM {self.TABLE_NAME}
            WHERE end_date = %s
            ORDER BY ann_date DESC, ts_code
        """
        params = [period]

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
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码查询财务指标数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, ann_date, end_date,
                   eps, dt_eps, bps, revenue_ps, capital_rese_ps,
                   roe, roe_waa, roe_dt, roa, roic,
                   debt_to_assets, assets_to_eqt, current_ratio, quick_ratio,
                   netprofit_margin, grossprofit_margin,
                   ar_turn, inv_turn, assets_turn,
                   basic_eps_yoy, netprofit_yoy, or_yoy, roe_yoy
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

        query += " ORDER BY ann_date DESC, end_date DESC"

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
        获取财务指标统计信息

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
                AVG(eps) as avg_eps,
                AVG(roe) as avg_roe,
                AVG(debt_to_assets) as avg_debt_ratio,
                AVG(netprofit_margin) as avg_netprofit_margin,
                MAX(roe) as max_roe,
                MIN(debt_to_assets) as min_debt_ratio
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

        result = self.execute_query(query, tuple(params) if params else None)
        if result:
            row = result[0]
            return {
                'total_count': row[0] or 0,
                'stock_count': row[1] or 0,
                'avg_eps': float(row[2]) if row[2] else 0.0,
                'avg_roe': float(row[3]) if row[3] else 0.0,
                'avg_debt_ratio': float(row[4]) if row[4] else 0.0,
                'avg_netprofit_margin': float(row[5]) if row[5] else 0.0,
                'max_roe': float(row[6]) if row[6] else 0.0,
                'min_debt_ratio': float(row[7]) if row[7] else 0.0
            }
        return {}

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新财务指标数据（UPSERT）

        注意：财务指标字段非常多(150+)，这里使用动态列映射，只插入DataFrame中存在的字段

        Args:
            df: 包含财务指标数据的 DataFrame

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

        # 获取DataFrame中所有存在的列（排除主键）
        all_cols = df.columns.tolist()
        primary_keys = ['ts_code', 'ann_date', 'end_date']

        # 需要更新的列（排除主键和审计字段）
        update_cols = [col for col in all_cols if col not in primary_keys and col not in ['created_at', 'updated_at']]

        # 准备插入数据
        values = []
        for _, row in df.iterrows():
            row_values = tuple(to_python_type(row.get(col)) for col in all_cols)
            values.append(row_values)

        # 构建动态UPSERT查询
        placeholders = ', '.join(['%s'] * len(all_cols))
        update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            ({', '.join(all_cols)})
            VALUES ({placeholders})
            ON CONFLICT (ts_code, ann_date, end_date)
            DO UPDATE SET
                {update_set},
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"✓ 批量插入/更新 {count} 条财务指标数据")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典（核心指标）"""
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'end_date': row[2],
            'eps': float(row[3]) if row[3] is not None else None,
            'dt_eps': float(row[4]) if row[4] is not None else None,
            'bps': float(row[5]) if row[5] is not None else None,
            'revenue_ps': float(row[6]) if row[6] is not None else None,
            'capital_rese_ps': float(row[7]) if row[7] is not None else None,
            'roe': float(row[8]) if row[8] is not None else None,
            'roe_waa': float(row[9]) if row[9] is not None else None,
            'roe_dt': float(row[10]) if row[10] is not None else None,
            'roa': float(row[11]) if row[11] is not None else None,
            'roic': float(row[12]) if row[12] is not None else None,
            'debt_to_assets': float(row[13]) if row[13] is not None else None,
            'assets_to_eqt': float(row[14]) if row[14] is not None else None,
            'current_ratio': float(row[15]) if row[15] is not None else None,
            'quick_ratio': float(row[16]) if row[16] is not None else None,
            'netprofit_margin': float(row[17]) if row[17] is not None else None,
            'grossprofit_margin': float(row[18]) if row[18] is not None else None,
            'ar_turn': float(row[19]) if row[19] is not None else None,
            'inv_turn': float(row[20]) if row[20] is not None else None,
            'assets_turn': float(row[21]) if row[21] is not None else None,
            'basic_eps_yoy': float(row[22]) if row[22] is not None else None,
            'netprofit_yoy': float(row[23]) if row[23] is not None else None,
            'or_yoy': float(row[24]) if row[24] is not None else None,
            'roe_yoy': float(row[25]) if row[25] is not None else None
        }
