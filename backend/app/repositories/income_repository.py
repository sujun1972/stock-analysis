"""
利润表数据Repository

管理income表的数据访问
"""

import pandas as pd
from typing import List, Dict, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class IncomeRepository(BaseRepository):
    """利润表数据Repository"""

    TABLE_NAME = "income"

    def __init__(self, db=None):
        super().__init__(db)

    def get_by_date_range(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询利润表数据

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            report_type: 报告类型（可选，1-12）
            comp_type: 公司类型（可选，1-4）
            limit: 限制返回记录数

        Returns:
            利润表数据列表

        Examples:
            >>> repo = IncomeRepository()
            >>> data = repo.get_by_date_range('20240101', '20241231')
            >>> data = repo.get_by_date_range(ts_code='600000.SH', report_type='1')
        """
        try:
            query = f"""
                SELECT ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type,
                       basic_eps, diluted_eps,
                       total_revenue, revenue, oper_cost,
                       sell_exp, admin_exp, fin_exp, rd_exp,
                       operate_profit, total_profit, income_tax,
                       n_income, n_income_attr_p, minority_gain,
                       ebit, ebitda,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE end_date >= %s AND end_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if report_type:
                query += " AND report_type = %s"
                params.append(report_type)

            if comp_type:
                query += " AND comp_type = %s"
                params.append(comp_type)

            query += " ORDER BY end_date DESC, ts_code"

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询利润表数据失败: {e}")
            raise QueryError(
                "利润表数据查询失败",
                error_code="INCOME_QUERY_FAILED",
                reason=str(e)
            )

    def get_by_date_range_with_offset(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询利润表数据（支持分页）

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            report_type: 报告类型（可选，1-12）
            comp_type: 公司类型（可选，1-4）
            limit: 限制返回记录数
            offset: 偏移量

        Returns:
            利润表数据列表

        Examples:
            >>> repo = IncomeRepository()
            >>> data = repo.get_by_date_range_with_offset('20240101', '20241231', limit=20, offset=0)
        """
        try:
            query = f"""
                SELECT ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type,
                       basic_eps, diluted_eps,
                       total_revenue, revenue, oper_cost,
                       sell_exp, admin_exp, fin_exp, rd_exp,
                       operate_profit, total_profit, income_tax,
                       n_income, n_income_attr_p, minority_gain,
                       ebit, ebitda,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE end_date >= %s AND end_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if report_type:
                query += " AND report_type = %s"
                params.append(report_type)

            if comp_type:
                query += " AND comp_type = %s"
                params.append(comp_type)

            query += " ORDER BY end_date DESC, ts_code"
            query += " LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询利润表数据失败: {e}")
            raise QueryError(
                "利润表数据查询失败",
                error_code="INCOME_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> Dict:
        """
        获取利润表统计信息

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            report_type: 报告类型（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = IncomeRepository()
            >>> stats = repo.get_statistics('20240101', '20241231')
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(total_revenue) as avg_revenue,
                    AVG(n_income) as avg_net_income,
                    AVG(n_income_attr_p) as avg_income_attr_p,
                    AVG(basic_eps) as avg_eps,
                    SUM(total_revenue) as sum_revenue,
                    SUM(n_income) as sum_net_income,
                    MAX(total_revenue) as max_revenue,
                    MAX(n_income) as max_net_income
                FROM {self.TABLE_NAME}
                WHERE end_date >= %s AND end_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if report_type:
                query += " AND report_type = %s"
                params.append(report_type)

            result = self.execute_query(query, tuple(params))

            if result:
                row = result[0]
                return {
                    'total_count': row[0] or 0,
                    'stock_count': row[1] or 0,
                    'avg_revenue': float(row[2]) if row[2] else 0.0,
                    'avg_net_income': float(row[3]) if row[3] else 0.0,
                    'avg_income_attr_p': float(row[4]) if row[4] else 0.0,
                    'avg_eps': float(row[5]) if row[5] else 0.0,
                    'sum_revenue': float(row[6]) if row[6] else 0.0,
                    'sum_net_income': float(row[7]) if row[7] else 0.0,
                    'max_revenue': float(row[8]) if row[8] else 0.0,
                    'max_net_income': float(row[9]) if row[9] else 0.0
                }

            return {
                'total_count': 0,
                'stock_count': 0,
                'avg_revenue': 0.0,
                'avg_net_income': 0.0,
                'avg_income_attr_p': 0.0,
                'avg_eps': 0.0,
                'sum_revenue': 0.0,
                'sum_net_income': 0.0,
                'max_revenue': 0.0,
                'max_net_income': 0.0
            }

        except Exception as e:
            logger.error(f"获取利润表统计信息失败: {e}")
            raise QueryError(
                "利润表统计查询失败",
                error_code="INCOME_STATISTICS_FAILED",
                reason=str(e)
            )

    def get_latest_end_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新报告期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新报告期（YYYYMMDD格式），如果没有数据返回None

        Examples:
            >>> repo = IncomeRepository()
            >>> latest_date = repo.get_latest_end_date()
            >>> latest_date = repo.get_latest_end_date(ts_code='600000.SH')
        """
        try:
            query = f"SELECT MAX(end_date) FROM {self.TABLE_NAME}"
            params = []

            if ts_code:
                query += " WHERE ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params) if params else None)

            if result and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新报告期失败: {e}")
            raise QueryError(
                "获取最新报告期失败",
                error_code="INCOME_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新利润表数据

        Args:
            df: 包含利润表数据的DataFrame

        Returns:
            受影响的记录数

        Examples:
            >>> repo = IncomeRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                ⚠️ 关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换numpy整数类型为Python int
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                # 转换numpy浮点类型为Python float
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备UPSERT查询（选择核心字段）
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, f_ann_date, end_date, report_type, comp_type, end_type,
                 basic_eps, diluted_eps,
                 total_revenue, revenue, oper_cost,
                 sell_exp, admin_exp, fin_exp, rd_exp,
                 operate_profit, total_profit, income_tax,
                 n_income, n_income_attr_p, minority_gain,
                 ebit, ebitda, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ts_code, end_date, report_type)
                DO UPDATE SET
                    ann_date = EXCLUDED.ann_date,
                    f_ann_date = EXCLUDED.f_ann_date,
                    comp_type = EXCLUDED.comp_type,
                    end_type = EXCLUDED.end_type,
                    basic_eps = EXCLUDED.basic_eps,
                    diluted_eps = EXCLUDED.diluted_eps,
                    total_revenue = EXCLUDED.total_revenue,
                    revenue = EXCLUDED.revenue,
                    oper_cost = EXCLUDED.oper_cost,
                    sell_exp = EXCLUDED.sell_exp,
                    admin_exp = EXCLUDED.admin_exp,
                    fin_exp = EXCLUDED.fin_exp,
                    rd_exp = EXCLUDED.rd_exp,
                    operate_profit = EXCLUDED.operate_profit,
                    total_profit = EXCLUDED.total_profit,
                    income_tax = EXCLUDED.income_tax,
                    n_income = EXCLUDED.n_income,
                    n_income_attr_p = EXCLUDED.n_income_attr_p,
                    minority_gain = EXCLUDED.minority_gain,
                    ebit = EXCLUDED.ebit,
                    ebitda = EXCLUDED.ebitda,
                    updated_at = NOW()
            """

            # 准备插入数据（对每个字段应用类型转换）
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('f_ann_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('report_type')),
                    to_python_type(row.get('comp_type')),
                    to_python_type(row.get('end_type')),
                    to_python_type(row.get('basic_eps')),
                    to_python_type(row.get('diluted_eps')),
                    to_python_type(row.get('total_revenue')),
                    to_python_type(row.get('revenue')),
                    to_python_type(row.get('oper_cost')),
                    to_python_type(row.get('sell_exp')),
                    to_python_type(row.get('admin_exp')),
                    to_python_type(row.get('fin_exp')),
                    to_python_type(row.get('rd_exp')),
                    to_python_type(row.get('operate_profit')),
                    to_python_type(row.get('total_profit')),
                    to_python_type(row.get('income_tax')),
                    to_python_type(row.get('n_income')),
                    to_python_type(row.get('n_income_attr_p')),
                    to_python_type(row.get('minority_gain')),
                    to_python_type(row.get('ebit')),
                    to_python_type(row.get('ebitda'))
                ))

            # 执行批量插入
            count = self.execute_batch(query, values)

            logger.info(f"成功插入/更新 {count} 条利润表记录")
            return count

        except Exception as e:
            logger.error(f"批量插入利润表数据失败: {e}")
            raise QueryError(
                "批量插入利润表数据失败",
                error_code="INCOME_BULK_UPSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = IncomeRepository()
            >>> count = repo.delete_by_date_range('20240101', '20241231')
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE end_date >= %s AND end_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            count = self.execute_update(query, tuple(params))

            logger.info(f"删除了 {count} 条利润表记录")
            return count

        except Exception as e:
            logger.error(f"删除利润表数据失败: {e}")
            raise QueryError(
                "删除利润表数据失败",
                error_code="INCOME_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, end_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            end_date: 报告期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            True 如果存在，否则 False

        Examples:
            >>> repo = IncomeRepository()
            >>> exists = repo.exists_by_date('20240331')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE end_date = %s"
            params = [end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查利润表数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None
    ) -> int:
        """
        获取记录总数（支持筛选）

        Args:
            start_date: 开始日期（报告期），格式：YYYYMMDD
            end_date: 结束日期（报告期），格式：YYYYMMDD
            ts_code: 股票代码（可选）
            report_type: 报告类型（可选）
            comp_type: 公司类型（可选）

        Returns:
            记录总数

        Examples:
            >>> repo = IncomeRepository()
            >>> count = repo.get_record_count('20240101', '20241231')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE end_date >= %s AND end_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if report_type:
                query += " AND report_type = %s"
                params.append(report_type)

            if comp_type:
                query += " AND comp_type = %s"
                params.append(comp_type)

            result = self.execute_query(query, tuple(params))

            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取利润表记录数失败: {e}")
            raise QueryError(
                "获取利润表记录数失败",
                error_code="INCOME_COUNT_FAILED",
                reason=str(e)
            )

    def get_by_period(
        self,
        period: str,
        ts_code: Optional[str] = None,
        report_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期类型查询数据（如20241Q1、20240331等）

        Args:
            period: 报告期（YYYYMMDD或YYYYQQ格式）
            ts_code: 股票代码（可选）
            report_type: 报告类型（可选）
            limit: 限制返回记录数

        Returns:
            利润表数据列表

        Examples:
            >>> repo = IncomeRepository()
            >>> data = repo.get_by_period('20240331')
            >>> data = repo.get_by_period('20241Q1', report_type='2')
        """
        return self.get_by_date_range(
            start_date=period,
            end_date=period,
            ts_code=ts_code,
            report_type=report_type,
            limit=limit
        )

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'f_ann_date': row[2],
            'end_date': row[3],
            'report_type': row[4],
            'comp_type': row[5],
            'end_type': row[6],
            'basic_eps': float(row[7]) if row[7] is not None else None,
            'diluted_eps': float(row[8]) if row[8] is not None else None,
            'total_revenue': float(row[9]) if row[9] is not None else None,
            'revenue': float(row[10]) if row[10] is not None else None,
            'oper_cost': float(row[11]) if row[11] is not None else None,
            'sell_exp': float(row[12]) if row[12] is not None else None,
            'admin_exp': float(row[13]) if row[13] is not None else None,
            'fin_exp': float(row[14]) if row[14] is not None else None,
            'rd_exp': float(row[15]) if row[15] is not None else None,
            'operate_profit': float(row[16]) if row[16] is not None else None,
            'total_profit': float(row[17]) if row[17] is not None else None,
            'income_tax': float(row[18]) if row[18] is not None else None,
            'n_income': float(row[19]) if row[19] is not None else None,
            'n_income_attr_p': float(row[20]) if row[20] is not None else None,
            'minority_gain': float(row[21]) if row[21] is not None else None,
            'ebit': float(row[22]) if row[22] is not None else None,
            'ebitda': float(row[23]) if row[23] is not None else None,
            'created_at': row[24].isoformat() if row[24] else None,
            'updated_at': row[25].isoformat() if row[25] else None
        }
