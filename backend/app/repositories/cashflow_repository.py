"""
现金流量表数据 Repository

管理 cashflow 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class CashflowRepository(BaseRepository):
    """现金流量表数据 Repository"""

    TABLE_NAME = "cashflow"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ CashflowRepository initialized")

    def get_total_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> int:
        """获取符合条件的记录总数"""
        try:
            conditions = []
            params = []
            conditions.append("ann_date >= %s")
            params.append(start_date or '19900101')
            conditions.append("ann_date <= %s")
            params.append(end_date or '29991231')
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)
            if period:
                conditions.append("end_date = %s")
                params.append(period)
            if report_type:
                conditions.append("report_type = %s")
                params.append(report_type)
            where_clause = " AND ".join(conditions)
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
            result = self.execute_query(query, tuple(params))
            return int(result[0][0]) if result else 0
        except Exception as e:
            logger.error(f"获取现金流量表记录总数失败: {e}")
            raise

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询现金流量表数据

        Args:
            start_date: 开始日期 (公告日期), 格式：YYYYMMDD
            end_date: 结束日期 (公告日期), 格式：YYYYMMDD
            ts_code: 股票代码（可选）
            period: 报告期（可选，格式：YYYYMMDD）
            report_type: 报告类型（可选，1-12）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = CashflowRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("ann_date >= %s")
                params.append(start_date)
            else:
                conditions.append("ann_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("ann_date <= %s")
                params.append(end_date)
            else:
                conditions.append("ann_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if period:
                conditions.append("end_date = %s")
                params.append(period)

            if report_type:
                conditions.append("report_type = %s")
                params.append(report_type)

            where_clause = " AND ".join(conditions)

            # 查询主要字段（核心现金流指标）
            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    f_ann_date,
                    end_date,
                    report_type,
                    comp_type,
                    end_type,
                    net_profit,
                    finan_exp,
                    -- 经营活动现金流
                    n_cashflow_act,
                    c_fr_sale_sg,
                    c_paid_goods_s,
                    c_paid_to_for_empl,
                    c_paid_for_taxes,
                    -- 投资活动现金流
                    n_cashflow_inv_act,
                    c_disp_withdrwl_invest,
                    c_pay_acq_const_fiolta,
                    -- 筹资活动现金流
                    n_cash_flows_fnc_act,
                    c_recp_borrow,
                    c_prepay_amt_borr,
                    -- 现金净额
                    n_incr_cash_cash_equ,
                    c_cash_equ_beg_period,
                    c_cash_equ_end_period,
                    -- 关键指标
                    free_cashflow,
                    im_net_cashflow_oper_act,
                    update_flag,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY ann_date DESC, ts_code
            """

            if limit:
                query += f" LIMIT {int(limit)}"

            if offset:
                query += f" OFFSET {int(offset)}"

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询现金流量表数据失败: {e}")
            raise

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
            'net_profit': row[7],
            'finan_exp': row[8],
            'n_cashflow_act': row[9],
            'c_fr_sale_sg': row[10],
            'c_paid_goods_s': row[11],
            'c_paid_to_for_empl': row[12],
            'c_paid_for_taxes': row[13],
            'n_cashflow_inv_act': row[14],
            'c_disp_withdrwl_invest': row[15],
            'c_pay_acq_const_fiolta': row[16],
            'n_cash_flows_fnc_act': row[17],
            'c_recp_borrow': row[18],
            'c_prepay_amt_borr': row[19],
            'n_incr_cash_cash_equ': row[20],
            'c_cash_equ_beg_period': row[21],
            'c_cash_equ_end_period': row[22],
            'free_cashflow': row[23],
            'im_net_cashflow_oper_act': row[24],
            'update_flag': row[25],
            'created_at': row[26],
            'updated_at': row[27]
        }

    def get_latest(self, ts_code: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        获取最新的现金流量表数据

        Args:
            ts_code: 股票代码（可选）
            limit: 返回记录数限制

        Returns:
            数据列表
        """
        try:
            where_clause = ""
            params = []

            if ts_code:
                where_clause = "WHERE ts_code = %s"
                params.append(ts_code)

            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    end_date,
                    report_type,
                    n_cashflow_act,
                    n_cashflow_inv_act,
                    n_cash_flows_fnc_act,
                    free_cashflow,
                    n_incr_cash_cash_equ
                FROM {self.TABLE_NAME}
                {where_clause}
                ORDER BY ann_date DESC, end_date DESC
                LIMIT {int(limit)}
            """

            result = self.execute_query(query, tuple(params) if params else ())
            return [
                {
                    'ts_code': row[0],
                    'ann_date': row[1],
                    'end_date': row[2],
                    'report_type': row[3],
                    'n_cashflow_act': row[4],
                    'n_cashflow_inv_act': row[5],
                    'n_cash_flows_fnc_act': row[6],
                    'free_cashflow': row[7],
                    'n_incr_cash_cash_equ': row[8]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"获取最新现金流量表数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取现金流量表统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("ann_date >= %s")
                params.append(start_date)
            else:
                conditions.append("ann_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("ann_date <= %s")
                params.append(end_date)
            else:
                conditions.append("ann_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(n_cashflow_act) as avg_operating_cf,
                    AVG(free_cashflow) as avg_free_cf,
                    MAX(n_cashflow_act) as max_operating_cf,
                    MIN(n_cashflow_act) as min_operating_cf
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            if result and len(result) > 0:
                row = result[0]
                return {
                    'total': row[0] or 0,
                    'stock_count': row[1] or 0,
                    'avg_operating_cf': float(row[2]) if row[2] is not None else 0.0,
                    'avg_free_cf': float(row[3]) if row[3] is not None else 0.0,
                    'max_operating_cf': float(row[4]) if row[4] is not None else 0.0,
                    'min_operating_cf': float(row[5]) if row[5] is not None else 0.0
                }
            return {
                'total': 0,
                'stock_count': 0,
                'avg_operating_cf': 0.0,
                'avg_free_cf': 0.0,
                'max_operating_cf': 0.0,
                'min_operating_cf': 0.0
            }

        except Exception as e:
            logger.error(f"获取现金流量表统计信息失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新现金流量表数据

        Args:
            df: 包含现金流量表数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = CashflowRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
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
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, ann_date, f_ann_date, end_date, comp_type, report_type, end_type,
                    net_profit, finan_exp,
                    c_fr_sale_sg, recp_tax_rends, n_depos_incr_fi, n_incr_loans_cb, n_inc_borr_oth_fi,
                    prem_fr_orig_contr, n_incr_insured_dep, n_reinsur_prem, n_incr_disp_tfa, ifc_cash_incr,
                    n_incr_disp_faas, n_incr_loans_oth_bank, n_cap_incr_repur, c_fr_oth_operate_a, c_inf_fr_operate_a,
                    c_paid_goods_s, c_paid_to_for_empl, c_paid_for_taxes, n_incr_clt_loan_adv, n_incr_dep_cbob,
                    c_pay_claims_orig_inco, pay_handling_chrg, pay_comm_insur_plcy, oth_cash_pay_oper_act, st_cash_out_act,
                    n_cashflow_act,
                    oth_recp_ral_inv_act, c_disp_withdrwl_invest, c_recp_return_invest, n_recp_disp_fiolta, n_recp_disp_sobu,
                    stot_inflows_inv_act, c_pay_acq_const_fiolta, c_paid_invest, n_disp_subs_oth_biz, oth_pay_ral_inv_act,
                    n_incr_pledge_loan, stot_out_inv_act, n_cashflow_inv_act,
                    c_recp_borrow, proc_issue_bonds, oth_cash_recp_ral_fnc_act, stot_cash_in_fnc_act, free_cashflow,
                    c_prepay_amt_borr, c_pay_dist_dpcp_int_exp, incl_dvd_profit_paid_sc_ms, oth_cashpay_ral_fnc_act,
                    stot_cashout_fnc_act, n_cash_flows_fnc_act, eff_fx_flu_cash,
                    n_incr_cash_cash_equ, c_cash_equ_beg_period, c_cash_equ_end_period,
                    c_recp_cap_contrib, incl_cash_rec_saims, uncon_invest_loss, prov_depr_assets, depr_fa_coga_dpba,
                    amort_intang_assets, lt_amort_deferred_exp, decr_deferred_exp, incr_acc_exp, loss_disp_fiolta,
                    loss_scr_fa, loss_fv_chg, invest_loss, decr_def_inc_tax_assets, incr_def_inc_tax_liab,
                    decr_inventories, decr_oper_payable, incr_oper_payable, others, im_net_cashflow_oper_act,
                    conv_debt_into_cap, conv_copbonds_due_within_1y, fa_fnc_leases, im_n_incr_cash_equ,
                    net_dism_capital_add, net_cash_rece_sec, credit_impa_loss, use_right_asset_dep, oth_loss_asset,
                    end_bal_cash, beg_bal_cash, end_bal_cash_equ, beg_bal_cash_equ,
                    update_flag
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s
                )
                ON CONFLICT (ts_code, end_date, report_type)
                DO UPDATE SET
                    ann_date = EXCLUDED.ann_date,
                    f_ann_date = EXCLUDED.f_ann_date,
                    comp_type = EXCLUDED.comp_type,
                    end_type = EXCLUDED.end_type,
                    net_profit = EXCLUDED.net_profit,
                    finan_exp = EXCLUDED.finan_exp,
                    n_cashflow_act = EXCLUDED.n_cashflow_act,
                    n_cashflow_inv_act = EXCLUDED.n_cashflow_inv_act,
                    n_cash_flows_fnc_act = EXCLUDED.n_cash_flows_fnc_act,
                    free_cashflow = EXCLUDED.free_cashflow,
                    update_flag = EXCLUDED.update_flag,
                    updated_at = NOW()
            """

            # 准备批量插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('f_ann_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('comp_type')),
                    to_python_type(row.get('report_type')),
                    to_python_type(row.get('end_type')),
                    # 净利润和费用
                    to_python_type(row.get('net_profit')),
                    to_python_type(row.get('finan_exp')),
                    # 经营活动现金流入（15个字段）
                    to_python_type(row.get('c_fr_sale_sg')),
                    to_python_type(row.get('recp_tax_rends')),
                    to_python_type(row.get('n_depos_incr_fi')),
                    to_python_type(row.get('n_incr_loans_cb')),
                    to_python_type(row.get('n_inc_borr_oth_fi')),
                    to_python_type(row.get('prem_fr_orig_contr')),
                    to_python_type(row.get('n_incr_insured_dep')),
                    to_python_type(row.get('n_reinsur_prem')),
                    to_python_type(row.get('n_incr_disp_tfa')),
                    to_python_type(row.get('ifc_cash_incr')),
                    to_python_type(row.get('n_incr_disp_faas')),
                    to_python_type(row.get('n_incr_loans_oth_bank')),
                    to_python_type(row.get('n_cap_incr_repur')),
                    to_python_type(row.get('c_fr_oth_operate_a')),
                    to_python_type(row.get('c_inf_fr_operate_a')),
                    # 经营活动现金流出（11个字段）
                    to_python_type(row.get('c_paid_goods_s')),
                    to_python_type(row.get('c_paid_to_for_empl')),
                    to_python_type(row.get('c_paid_for_taxes')),
                    to_python_type(row.get('n_incr_clt_loan_adv')),
                    to_python_type(row.get('n_incr_dep_cbob')),
                    to_python_type(row.get('c_pay_claims_orig_inco')),
                    to_python_type(row.get('pay_handling_chrg')),
                    to_python_type(row.get('pay_comm_insur_plcy')),
                    to_python_type(row.get('oth_cash_pay_oper_act')),
                    to_python_type(row.get('st_cash_out_act')),
                    to_python_type(row.get('n_cashflow_act')),
                    # 投资活动现金流（13个字段）
                    to_python_type(row.get('oth_recp_ral_inv_act')),
                    to_python_type(row.get('c_disp_withdrwl_invest')),
                    to_python_type(row.get('c_recp_return_invest')),
                    to_python_type(row.get('n_recp_disp_fiolta')),
                    to_python_type(row.get('n_recp_disp_sobu')),
                    to_python_type(row.get('stot_inflows_inv_act')),
                    to_python_type(row.get('c_pay_acq_const_fiolta')),
                    to_python_type(row.get('c_paid_invest')),
                    to_python_type(row.get('n_disp_subs_oth_biz')),
                    to_python_type(row.get('oth_pay_ral_inv_act')),
                    to_python_type(row.get('n_incr_pledge_loan')),
                    to_python_type(row.get('stot_out_inv_act')),
                    to_python_type(row.get('n_cashflow_inv_act')),
                    # 筹资活动现金流（13个字段）
                    to_python_type(row.get('c_recp_borrow')),
                    to_python_type(row.get('proc_issue_bonds')),
                    to_python_type(row.get('oth_cash_recp_ral_fnc_act')),
                    to_python_type(row.get('stot_cash_in_fnc_act')),
                    to_python_type(row.get('free_cashflow')),
                    to_python_type(row.get('c_prepay_amt_borr')),
                    to_python_type(row.get('c_pay_dist_dpcp_int_exp')),
                    to_python_type(row.get('incl_dvd_profit_paid_sc_ms')),
                    to_python_type(row.get('oth_cashpay_ral_fnc_act')),
                    to_python_type(row.get('stot_cashout_fnc_act')),
                    to_python_type(row.get('n_cash_flows_fnc_act')),
                    to_python_type(row.get('eff_fx_flu_cash')),
                    # 现金及现金等价物（3个字段）
                    to_python_type(row.get('n_incr_cash_cash_equ')),
                    to_python_type(row.get('c_cash_equ_beg_period')),
                    to_python_type(row.get('c_cash_equ_end_period')),
                    # 其他项目（43个字段）
                    to_python_type(row.get('c_recp_cap_contrib')),
                    to_python_type(row.get('incl_cash_rec_saims')),
                    to_python_type(row.get('uncon_invest_loss')),
                    to_python_type(row.get('prov_depr_assets')),
                    to_python_type(row.get('depr_fa_coga_dpba')),
                    to_python_type(row.get('amort_intang_assets')),
                    to_python_type(row.get('lt_amort_deferred_exp')),
                    to_python_type(row.get('decr_deferred_exp')),
                    to_python_type(row.get('incr_acc_exp')),
                    to_python_type(row.get('loss_disp_fiolta')),
                    to_python_type(row.get('loss_scr_fa')),
                    to_python_type(row.get('loss_fv_chg')),
                    to_python_type(row.get('invest_loss')),
                    to_python_type(row.get('decr_def_inc_tax_assets')),
                    to_python_type(row.get('incr_def_inc_tax_liab')),
                    to_python_type(row.get('decr_inventories')),
                    to_python_type(row.get('decr_oper_payable')),
                    to_python_type(row.get('incr_oper_payable')),
                    to_python_type(row.get('others')),
                    to_python_type(row.get('im_net_cashflow_oper_act')),
                    to_python_type(row.get('conv_debt_into_cap')),
                    to_python_type(row.get('conv_copbonds_due_within_1y')),
                    to_python_type(row.get('fa_fnc_leases')),
                    to_python_type(row.get('im_n_incr_cash_equ')),
                    to_python_type(row.get('net_dism_capital_add')),
                    to_python_type(row.get('net_cash_rece_sec')),
                    to_python_type(row.get('credit_impa_loss')),
                    to_python_type(row.get('use_right_asset_dep')),
                    to_python_type(row.get('oth_loss_asset')),
                    to_python_type(row.get('end_bal_cash')),
                    to_python_type(row.get('beg_bal_cash')),
                    to_python_type(row.get('end_bal_cash_equ')),
                    to_python_type(row.get('beg_bal_cash_equ')),
                    # 更新标志
                    to_python_type(row.get('update_flag'))
                ))

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"✓ 批量插入/更新 {count} 条现金流量表记录")
            return count

        except Exception as e:
            logger.error(f"批量插入/更新现金流量表数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数
        """
        try:
            conditions = ["ann_date >= %s", "ann_date <= %s"]
            params = [start_date, end_date]

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions)

            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            count = self.execute_update(query, tuple(params))
            logger.info(f"✓ 删除 {count} 条现金流量表记录")
            return count

        except Exception as e:
            logger.error(f"删除现金流量表数据失败: {e}")
            raise
