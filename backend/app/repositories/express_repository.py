"""
业绩快报数据 Repository

管理 express 表的数据访问
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class ExpressRepository(BaseRepository):
    """业绩快报数据 Repository"""

    TABLE_NAME = "express"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ ExpressRepository initialized")

    def get_total_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        period: Optional[str] = None
    ) -> int:
        """获取符合条件的记录总数"""
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]
            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)
            if period:
                query += " AND end_date = %s"
                params.append(period)
            result = self.execute_query(query, tuple(params))
            return int(result[0][0]) if result else 0
        except Exception as e:
            logger.error(f"获取业绩快报记录总数失败: {e}")
            raise

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询业绩快报数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, ann_date, end_date, revenue, operate_profit,
                   total_profit, n_income, total_assets, total_hldr_eqy_exc_min_int,
                   diluted_eps, diluted_roe, yoy_net_profit, bps,
                   yoy_sales, yoy_op, yoy_tp, yoy_dedu_np, yoy_eps, yoy_roe,
                   growth_assets, yoy_equity, growth_bps,
                   or_last_year, op_last_year, tp_last_year, np_last_year, eps_last_year,
                   open_net_assets, open_bps, perf_summary, is_audit, remark
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

        if offset:
            query += " OFFSET %s"
            params.append(offset)

        result = self.execute_query(query, tuple(params))
        return [self._row_to_dict(row) for row in result]

    def get_by_period(
        self,
        period: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期查询业绩快报数据

        Args:
            period: 报告期，格式：YYYYMMDD（如20231231表示年报）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, ann_date, end_date, revenue, operate_profit,
                   total_profit, n_income, total_assets, total_hldr_eqy_exc_min_int,
                   diluted_eps, diluted_roe, yoy_net_profit, bps,
                   yoy_sales, yoy_op, yoy_tp, yoy_dedu_np, yoy_eps, yoy_roe,
                   growth_assets, yoy_equity, growth_bps,
                   or_last_year, op_last_year, tp_last_year, np_last_year, eps_last_year,
                   open_net_assets, open_bps, perf_summary, is_audit, remark
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
        按股票代码查询业绩快报数据

        Args:
            ts_code: 股票代码
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            limit: 限制返回数量

        Returns:
            数据列表
        """
        query = f"""
            SELECT ts_code, ann_date, end_date, revenue, operate_profit,
                   total_profit, n_income, total_assets, total_hldr_eqy_exc_min_int,
                   diluted_eps, diluted_roe, yoy_net_profit, bps,
                   yoy_sales, yoy_op, yoy_tp, yoy_dedu_np, yoy_eps, yoy_roe,
                   growth_assets, yoy_equity, growth_bps,
                   or_last_year, op_last_year, tp_last_year, np_last_year, eps_last_year,
                   open_net_assets, open_bps, perf_summary, is_audit, remark
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
        获取业绩快报统计信息

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
                AVG(revenue) as avg_revenue,
                AVG(n_income) as avg_n_income,
                AVG(diluted_eps) as avg_eps,
                AVG(diluted_roe) as avg_roe,
                MAX(revenue) as max_revenue,
                MIN(revenue) as min_revenue
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
                'avg_revenue': float(row[2]) if row[2] else 0.0,
                'avg_n_income': float(row[3]) if row[3] else 0.0,
                'avg_eps': float(row[4]) if row[4] else 0.0,
                'avg_roe': float(row[5]) if row[5] else 0.0,
                'max_revenue': float(row[6]) if row[6] else 0.0,
                'min_revenue': float(row[7]) if row[7] else 0.0
            }
        return {}

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新业绩快报数据（UPSERT）

        Args:
            df: 包含业绩快报数据的 DataFrame

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
                to_python_type(row.get('ann_date')),
                to_python_type(row.get('end_date')),
                to_python_type(row.get('revenue')),
                to_python_type(row.get('operate_profit')),
                to_python_type(row.get('total_profit')),
                to_python_type(row.get('n_income')),
                to_python_type(row.get('total_assets')),
                to_python_type(row.get('total_hldr_eqy_exc_min_int')),
                to_python_type(row.get('diluted_eps')),
                to_python_type(row.get('diluted_roe')),
                to_python_type(row.get('yoy_net_profit')),
                to_python_type(row.get('bps')),
                to_python_type(row.get('yoy_sales')),
                to_python_type(row.get('yoy_op')),
                to_python_type(row.get('yoy_tp')),
                to_python_type(row.get('yoy_dedu_np')),
                to_python_type(row.get('yoy_eps')),
                to_python_type(row.get('yoy_roe')),
                to_python_type(row.get('growth_assets')),
                to_python_type(row.get('yoy_equity')),
                to_python_type(row.get('growth_bps')),
                to_python_type(row.get('or_last_year')),
                to_python_type(row.get('op_last_year')),
                to_python_type(row.get('tp_last_year')),
                to_python_type(row.get('np_last_year')),
                to_python_type(row.get('eps_last_year')),
                to_python_type(row.get('open_net_assets')),
                to_python_type(row.get('open_bps')),
                to_python_type(row.get('perf_summary')),
                to_python_type(row.get('is_audit')),
                to_python_type(row.get('remark'))
            ))

        # UPSERT 查询
        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (ts_code, ann_date, end_date, revenue, operate_profit,
             total_profit, n_income, total_assets, total_hldr_eqy_exc_min_int,
             diluted_eps, diluted_roe, yoy_net_profit, bps,
             yoy_sales, yoy_op, yoy_tp, yoy_dedu_np, yoy_eps, yoy_roe,
             growth_assets, yoy_equity, growth_bps,
             or_last_year, op_last_year, tp_last_year, np_last_year, eps_last_year,
             open_net_assets, open_bps, perf_summary, is_audit, remark)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts_code, ann_date, end_date)
            DO UPDATE SET
                revenue = EXCLUDED.revenue,
                operate_profit = EXCLUDED.operate_profit,
                total_profit = EXCLUDED.total_profit,
                n_income = EXCLUDED.n_income,
                total_assets = EXCLUDED.total_assets,
                total_hldr_eqy_exc_min_int = EXCLUDED.total_hldr_eqy_exc_min_int,
                diluted_eps = EXCLUDED.diluted_eps,
                diluted_roe = EXCLUDED.diluted_roe,
                yoy_net_profit = EXCLUDED.yoy_net_profit,
                bps = EXCLUDED.bps,
                yoy_sales = EXCLUDED.yoy_sales,
                yoy_op = EXCLUDED.yoy_op,
                yoy_tp = EXCLUDED.yoy_tp,
                yoy_dedu_np = EXCLUDED.yoy_dedu_np,
                yoy_eps = EXCLUDED.yoy_eps,
                yoy_roe = EXCLUDED.yoy_roe,
                growth_assets = EXCLUDED.growth_assets,
                yoy_equity = EXCLUDED.yoy_equity,
                growth_bps = EXCLUDED.growth_bps,
                or_last_year = EXCLUDED.or_last_year,
                op_last_year = EXCLUDED.op_last_year,
                tp_last_year = EXCLUDED.tp_last_year,
                np_last_year = EXCLUDED.np_last_year,
                eps_last_year = EXCLUDED.eps_last_year,
                open_net_assets = EXCLUDED.open_net_assets,
                open_bps = EXCLUDED.open_bps,
                perf_summary = EXCLUDED.perf_summary,
                is_audit = EXCLUDED.is_audit,
                remark = EXCLUDED.remark,
                updated_at = NOW()
        """

        count = self.execute_batch(query, values)
        logger.info(f"✓ 批量插入/更新 {count} 条业绩快报数据")
        return count

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'end_date': row[2],
            'revenue': float(row[3]) if row[3] is not None else None,
            'operate_profit': float(row[4]) if row[4] is not None else None,
            'total_profit': float(row[5]) if row[5] is not None else None,
            'n_income': float(row[6]) if row[6] is not None else None,
            'total_assets': float(row[7]) if row[7] is not None else None,
            'total_hldr_eqy_exc_min_int': float(row[8]) if row[8] is not None else None,
            'diluted_eps': float(row[9]) if row[9] is not None else None,
            'diluted_roe': float(row[10]) if row[10] is not None else None,
            'yoy_net_profit': float(row[11]) if row[11] is not None else None,
            'bps': float(row[12]) if row[12] is not None else None,
            'yoy_sales': float(row[13]) if row[13] is not None else None,
            'yoy_op': float(row[14]) if row[14] is not None else None,
            'yoy_tp': float(row[15]) if row[15] is not None else None,
            'yoy_dedu_np': float(row[16]) if row[16] is not None else None,
            'yoy_eps': float(row[17]) if row[17] is not None else None,
            'yoy_roe': float(row[18]) if row[18] is not None else None,
            'growth_assets': float(row[19]) if row[19] is not None else None,
            'yoy_equity': float(row[20]) if row[20] is not None else None,
            'growth_bps': float(row[21]) if row[21] is not None else None,
            'or_last_year': float(row[22]) if row[22] is not None else None,
            'op_last_year': float(row[23]) if row[23] is not None else None,
            'tp_last_year': float(row[24]) if row[24] is not None else None,
            'np_last_year': float(row[25]) if row[25] is not None else None,
            'eps_last_year': float(row[26]) if row[26] is not None else None,
            'open_net_assets': float(row[27]) if row[27] is not None else None,
            'open_bps': float(row[28]) if row[28] is not None else None,
            'perf_summary': row[29],
            'is_audit': int(row[30]) if row[30] is not None else None,
            'remark': row[31]
        }
