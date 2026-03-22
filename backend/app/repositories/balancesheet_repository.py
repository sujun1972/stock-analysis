"""
资产负债表数据 Repository

管理 balancesheet 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class BalancesheetRepository(BaseRepository):
    """资产负债表数据 Repository"""

    TABLE_NAME = "balancesheet"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ BalancesheetRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询资产负债表数据

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
            >>> repo = BalancesheetRepository()
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

            # 查询主要字段（选择最常用的字段）
            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    f_ann_date,
                    end_date,
                    report_type,
                    comp_type,
                    end_type,
                    total_share,
                    cap_rese,
                    undistr_porfit,
                    surplus_rese,
                    money_cap,
                    total_cur_assets,
                    total_nca,
                    total_assets,
                    total_cur_liab,
                    total_ncl,
                    total_liab,
                    total_hldr_eqy_exc_min_int,
                    total_hldr_eqy_inc_min_int,
                    total_liab_hldr_eqy,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY ann_date DESC, ts_code ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询资产负债表数据失败: {e}")
            raise

    def get_by_code_and_period(
        self,
        ts_code: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        report_type: str = '1',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按股票代码和报告期查询资产负债表数据

        Args:
            ts_code: 股票代码
            start_period: 开始报告期，格式：YYYYMMDD
            end_period: 结束报告期，格式：YYYYMMDD
            report_type: 报告类型（默认1-合并报表）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = BalancesheetRepository()
            >>> data = repo.get_by_code_and_period('600000.SH', '20230331', '20231231')
        """
        try:
            conditions = ["ts_code = %s", "report_type = %s"]
            params = [ts_code, report_type]

            if start_period:
                conditions.append("end_date >= %s")
                params.append(start_period)

            if end_period:
                conditions.append("end_date <= %s")
                params.append(end_period)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    f_ann_date,
                    end_date,
                    report_type,
                    comp_type,
                    total_assets,
                    total_liab,
                    total_hldr_eqy_inc_min_int,
                    total_liab_hldr_eqy
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY end_date DESC
            """

            if limit:
                query += f" LIMIT {limit}"

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict_simple(row) for row in result]

        except Exception as e:
            logger.error(f"按代码和报告期查询资产负债表数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取资产负债表统计信息

        Args:
            start_date: 开始日期（公告日期），格式：YYYYMMDD
            end_date: 结束日期（公告日期），格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = BalancesheetRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
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
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as total_stocks,
                    COUNT(DISTINCT end_date) as total_periods,
                    AVG(total_assets) as avg_total_assets,
                    AVG(total_liab) as avg_total_liab,
                    AVG(total_hldr_eqy_inc_min_int) as avg_equity
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_records': row[0] or 0,
                    'total_stocks': row[1] or 0,
                    'total_periods': row[2] or 0,
                    'avg_total_assets': float(row[3]) if row[3] else 0.0,
                    'avg_total_liab': float(row[4]) if row[4] else 0.0,
                    'avg_equity': float(row[5]) if row[5] else 0.0,
                }

            return {
                'total_records': 0,
                'total_stocks': 0,
                'total_periods': 0,
                'avg_total_assets': 0.0,
                'avg_total_liab': 0.0,
                'avg_equity': 0.0,
            }

        except Exception as e:
            logger.error(f"获取资产负债表统计信息失败: {e}")
            raise

    def get_latest_ann_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新公告日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新公告日期 YYYYMMDD，如果没有数据则返回 None

        Examples:
            >>> repo = BalancesheetRepository()
            >>> latest_date = repo.get_latest_ann_date()
        """
        try:
            query = f"""
                SELECT MAX(ann_date) as latest_date
                FROM {self.TABLE_NAME}
            """

            params = []
            if ts_code:
                query = f"""
                    SELECT MAX(ann_date) as latest_date
                    FROM {self.TABLE_NAME}
                    WHERE ts_code = %s
                """
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            if result and len(result) > 0 and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新公告日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新资产负债表数据

        Args:
            df: 包含资产负债表数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = BalancesheetRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            # 注意：psycopg2无法直接处理numpy类型，必须转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                ⚠️ 关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换numpy整数/浮点类型为Python类型
                if isinstance(value, (pd.Int64Dtype, int, float)) or hasattr(value, 'item'):
                    try:
                        if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                            return float(value)
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                return value

            # 准备插入数据（158个字段）
            # 资产负债表包含大量字段：资产、负债、所有者权益等140+字段
            # 必须确保元组字段数与VALUES子句占位符数量一致（158个%s）
            values = []
            for idx, row in df.iterrows():
                try:
                    tuple_data = (
                        row.get('ts_code'),
                        row.get('ann_date'),
                    row.get('end_date'),
                    row.get('report_type'),
                    row.get('comp_type'),
                    row.get('f_ann_date'),
                    row.get('end_type'),
                    to_python_type(row.get('total_share')),
                    to_python_type(row.get('cap_rese')),
                    to_python_type(row.get('undistr_porfit')),
                    to_python_type(row.get('surplus_rese')),
                    to_python_type(row.get('special_rese')),
                    to_python_type(row.get('money_cap')),
                    to_python_type(row.get('trad_asset')),
                    to_python_type(row.get('notes_receiv')),
                    to_python_type(row.get('accounts_receiv')),
                    to_python_type(row.get('oth_receiv')),
                    to_python_type(row.get('prepayment')),
                    to_python_type(row.get('div_receiv')),
                    to_python_type(row.get('int_receiv')),
                    to_python_type(row.get('inventories')),
                    to_python_type(row.get('amor_exp')),
                    to_python_type(row.get('nca_within_1y')),
                    to_python_type(row.get('sett_rsrv')),
                    to_python_type(row.get('loanto_oth_bank_fi')),
                    to_python_type(row.get('premium_receiv')),
                    to_python_type(row.get('reinsur_receiv')),
                    to_python_type(row.get('reinsur_res_receiv')),
                    to_python_type(row.get('pur_resale_fa')),
                    to_python_type(row.get('oth_cur_assets')),
                    to_python_type(row.get('total_cur_assets')),
                    to_python_type(row.get('fa_avail_for_sale')),
                    to_python_type(row.get('htm_invest')),
                    to_python_type(row.get('lt_eqt_invest')),
                    to_python_type(row.get('invest_real_estate')),
                    to_python_type(row.get('time_deposits')),
                    to_python_type(row.get('oth_assets')),
                    to_python_type(row.get('lt_rec')),
                    to_python_type(row.get('fix_assets')),
                    to_python_type(row.get('cip')),
                    to_python_type(row.get('const_materials')),
                    to_python_type(row.get('fixed_assets_disp')),
                    to_python_type(row.get('produc_bio_assets')),
                    to_python_type(row.get('oil_and_gas_assets')),
                    to_python_type(row.get('intan_assets')),
                    to_python_type(row.get('r_and_d')),
                    to_python_type(row.get('goodwill')),
                    to_python_type(row.get('lt_amor_exp')),
                    to_python_type(row.get('defer_tax_assets')),
                    to_python_type(row.get('decr_in_disbur')),
                    to_python_type(row.get('oth_nca')),
                    to_python_type(row.get('total_nca')),
                    to_python_type(row.get('cash_reser_cb')),
                    to_python_type(row.get('depos_in_oth_bfi')),
                    to_python_type(row.get('prec_metals')),
                    to_python_type(row.get('deriv_assets')),
                    to_python_type(row.get('rr_reins_une_prem')),
                    to_python_type(row.get('rr_reins_outstd_cla')),
                    to_python_type(row.get('rr_reins_lins_liab')),
                    to_python_type(row.get('rr_reins_lthins_liab')),
                    to_python_type(row.get('refund_depos')),
                    to_python_type(row.get('ph_pledge_loans')),
                    to_python_type(row.get('refund_cap_depos')),
                    to_python_type(row.get('indep_acct_assets')),
                    to_python_type(row.get('client_depos')),
                    to_python_type(row.get('client_prov')),
                    to_python_type(row.get('transac_seat_fee')),
                    to_python_type(row.get('invest_as_receiv')),
                    to_python_type(row.get('total_assets')),
                    to_python_type(row.get('lt_borr')),
                    to_python_type(row.get('st_borr')),
                    to_python_type(row.get('cb_borr')),
                    to_python_type(row.get('depos_ib_deposits')),
                    to_python_type(row.get('loan_oth_bank')),
                    to_python_type(row.get('trading_fl')),
                    to_python_type(row.get('notes_payable')),
                    to_python_type(row.get('acct_payable')),
                    to_python_type(row.get('adv_receipts')),
                    to_python_type(row.get('sold_for_repur_fa')),
                    to_python_type(row.get('comm_payable')),
                    to_python_type(row.get('payroll_payable')),
                    to_python_type(row.get('taxes_payable')),
                    to_python_type(row.get('int_payable')),
                    to_python_type(row.get('div_payable')),
                    to_python_type(row.get('oth_payable')),
                    to_python_type(row.get('acc_exp')),
                    to_python_type(row.get('deferred_inc')),
                    to_python_type(row.get('st_bonds_payable')),
                    to_python_type(row.get('payable_to_reinsurer')),
                    to_python_type(row.get('rsrv_insur_cont')),
                    to_python_type(row.get('acting_trading_sec')),
                    to_python_type(row.get('acting_uw_sec')),
                    to_python_type(row.get('non_cur_liab_due_1y')),
                    to_python_type(row.get('oth_cur_liab')),
                    to_python_type(row.get('total_cur_liab')),
                    to_python_type(row.get('bond_payable')),
                    to_python_type(row.get('lt_payable')),
                    to_python_type(row.get('specific_payables')),
                    to_python_type(row.get('estimated_liab')),
                    to_python_type(row.get('defer_tax_liab')),
                    to_python_type(row.get('defer_inc_non_cur_liab')),
                    to_python_type(row.get('oth_ncl')),
                    to_python_type(row.get('total_ncl')),
                    to_python_type(row.get('depos_oth_bfi')),
                    to_python_type(row.get('deriv_liab')),
                    to_python_type(row.get('depos')),
                    to_python_type(row.get('agency_bus_liab')),
                    to_python_type(row.get('oth_liab')),
                    to_python_type(row.get('prem_receiv_adva')),
                    to_python_type(row.get('depos_received')),
                    to_python_type(row.get('ph_invest')),
                    to_python_type(row.get('reser_une_prem')),
                    to_python_type(row.get('reser_outstd_claims')),
                    to_python_type(row.get('reser_lins_liab')),
                    to_python_type(row.get('reser_lthins_liab')),
                    to_python_type(row.get('indept_acc_liab')),
                    to_python_type(row.get('pledge_borr')),
                    to_python_type(row.get('indem_payable')),
                    to_python_type(row.get('policy_div_payable')),
                    to_python_type(row.get('total_liab')),
                    to_python_type(row.get('treasury_share')),
                    to_python_type(row.get('ordin_risk_reser')),
                    to_python_type(row.get('forex_differ')),
                    to_python_type(row.get('invest_loss_unconf')),
                    to_python_type(row.get('minority_int')),
                    to_python_type(row.get('total_hldr_eqy_exc_min_int')),
                    to_python_type(row.get('total_hldr_eqy_inc_min_int')),
                    to_python_type(row.get('total_liab_hldr_eqy')),
                    to_python_type(row.get('lt_payroll_payable')),
                    to_python_type(row.get('oth_comp_income')),
                    to_python_type(row.get('oth_eqt_tools')),
                    to_python_type(row.get('oth_eqt_tools_p_shr')),
                    to_python_type(row.get('lending_funds')),
                    to_python_type(row.get('acc_receivable')),
                    to_python_type(row.get('st_fin_payable')),
                    to_python_type(row.get('payables')),
                    to_python_type(row.get('hfs_assets')),
                    to_python_type(row.get('hfs_sales')),
                    to_python_type(row.get('cost_fin_assets')),
                    to_python_type(row.get('fair_value_fin_assets')),
                    to_python_type(row.get('cip_total')),
                    to_python_type(row.get('oth_pay_total')),
                    to_python_type(row.get('long_pay_total')),
                    to_python_type(row.get('debt_invest')),
                    to_python_type(row.get('oth_debt_invest')),
                    to_python_type(row.get('oth_eq_invest')),
                    to_python_type(row.get('oth_illiq_fin_assets')),
                    to_python_type(row.get('oth_eq_ppbond')),
                    to_python_type(row.get('receiv_financing')),
                    to_python_type(row.get('use_right_assets')),
                    to_python_type(row.get('lease_liab')),
                    to_python_type(row.get('contract_assets')),
                    to_python_type(row.get('contract_liab')),
                    to_python_type(row.get('accounts_receiv_bill')),
                    to_python_type(row.get('accounts_pay')),
                    to_python_type(row.get('oth_rcv_total')),
                    to_python_type(row.get('fix_assets_total')),
                    row.get('update_flag'),
                    )
                    values.append(tuple_data)
                except Exception as row_error:
                    logger.error(f"处理第 {idx} 行数据时出错: {row_error}")
                    raise

            if not values:
                logger.warning("没有准备任何数据")
                return 0

            # 执行批量 UPSERT
            # ON CONFLICT: 根据主键(ts_code, ann_date, end_date, report_type)判断冲突
            # DO UPDATE: 冲突时更新所有字段，实现数据同步的幂等性
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, end_date, report_type, comp_type, f_ann_date, end_type, total_share, cap_rese, undistr_porfit,
                 surplus_rese, special_rese, money_cap, trad_asset, notes_receiv, accounts_receiv, oth_receiv, prepayment,
                 div_receiv, int_receiv, inventories, amor_exp, nca_within_1y, sett_rsrv, loanto_oth_bank_fi, premium_receiv,
                 reinsur_receiv, reinsur_res_receiv, pur_resale_fa, oth_cur_assets, total_cur_assets, fa_avail_for_sale,
                 htm_invest, lt_eqt_invest, invest_real_estate, time_deposits, oth_assets, lt_rec, fix_assets, cip,
                 const_materials, fixed_assets_disp, produc_bio_assets, oil_and_gas_assets, intan_assets, r_and_d, goodwill,
                 lt_amor_exp, defer_tax_assets, decr_in_disbur, oth_nca, total_nca, cash_reser_cb, depos_in_oth_bfi,
                 prec_metals, deriv_assets, rr_reins_une_prem, rr_reins_outstd_cla, rr_reins_lins_liab, rr_reins_lthins_liab,
                 refund_depos, ph_pledge_loans, refund_cap_depos, indep_acct_assets, client_depos, client_prov, transac_seat_fee,
                 invest_as_receiv, total_assets, lt_borr, st_borr, cb_borr, depos_ib_deposits, loan_oth_bank, trading_fl,
                 notes_payable, acct_payable, adv_receipts, sold_for_repur_fa, comm_payable, payroll_payable, taxes_payable,
                 int_payable, div_payable, oth_payable, acc_exp, deferred_inc, st_bonds_payable, payable_to_reinsurer,
                 rsrv_insur_cont, acting_trading_sec, acting_uw_sec, non_cur_liab_due_1y, oth_cur_liab, total_cur_liab,
                 bond_payable, lt_payable, specific_payables, estimated_liab, defer_tax_liab, defer_inc_non_cur_liab, oth_ncl,
                 total_ncl, depos_oth_bfi, deriv_liab, depos, agency_bus_liab, oth_liab, prem_receiv_adva, depos_received,
                 ph_invest, reser_une_prem, reser_outstd_claims, reser_lins_liab, reser_lthins_liab, indept_acc_liab,
                 pledge_borr, indem_payable, policy_div_payable, total_liab, treasury_share, ordin_risk_reser, forex_differ,
                 invest_loss_unconf, minority_int, total_hldr_eqy_exc_min_int, total_hldr_eqy_inc_min_int, total_liab_hldr_eqy,
                 lt_payroll_payable, oth_comp_income, oth_eqt_tools, oth_eqt_tools_p_shr, lending_funds, acc_receivable,
                 st_fin_payable, payables, hfs_assets, hfs_sales, cost_fin_assets, fair_value_fin_assets, cip_total,
                 oth_pay_total, long_pay_total, debt_invest, oth_debt_invest, oth_eq_invest, oth_illiq_fin_assets,
                 oth_eq_ppbond, receiv_financing, use_right_assets, lease_liab, contract_assets, contract_liab,
                 accounts_receiv_bill, accounts_pay, oth_rcv_total, fix_assets_total, update_flag)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s)
                ON CONFLICT (ts_code, ann_date, end_date, report_type)
                DO UPDATE SET
                    comp_type = EXCLUDED.comp_type,
                    f_ann_date = EXCLUDED.f_ann_date,
                    end_type = EXCLUDED.end_type,
                    total_share = EXCLUDED.total_share,
                    cap_rese = EXCLUDED.cap_rese,
                    undistr_porfit = EXCLUDED.undistr_porfit,
                    total_assets = EXCLUDED.total_assets,
                    total_liab = EXCLUDED.total_liab,
                    total_hldr_eqy_inc_min_int = EXCLUDED.total_hldr_eqy_inc_min_int,
                    update_flag = EXCLUDED.update_flag,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条资产负债表记录")

            return count

        except Exception as e:
            logger.error(f"批量插入资产负债表数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期（公告日期），格式：YYYYMMDD
            end_date: 结束日期（公告日期），格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = BalancesheetRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
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
            logger.info(f"成功删除 {count} 条资产负债表记录")

            return count

        except Exception as e:
            logger.error(f"删除资产负债表数据失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典（主要字段）

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'f_ann_date': row[2],
            'end_date': row[3],
            'report_type': row[4],
            'comp_type': row[5],
            'end_type': row[6],
            'total_share': float(row[7]) if row[7] is not None else None,
            'cap_rese': float(row[8]) if row[8] is not None else None,
            'undistr_porfit': float(row[9]) if row[9] is not None else None,
            'surplus_rese': float(row[10]) if row[10] is not None else None,
            'money_cap': float(row[11]) if row[11] is not None else None,
            'total_cur_assets': float(row[12]) if row[12] is not None else None,
            'total_nca': float(row[13]) if row[13] is not None else None,
            'total_assets': float(row[14]) if row[14] is not None else None,
            'total_cur_liab': float(row[15]) if row[15] is not None else None,
            'total_ncl': float(row[16]) if row[16] is not None else None,
            'total_liab': float(row[17]) if row[17] is not None else None,
            'total_hldr_eqy_exc_min_int': float(row[18]) if row[18] is not None else None,
            'total_hldr_eqy_inc_min_int': float(row[19]) if row[19] is not None else None,
            'total_liab_hldr_eqy': float(row[20]) if row[20] is not None else None,
            'created_at': row[21].isoformat() + 'Z' if row[21] else None,
            'updated_at': row[22].isoformat() + 'Z' if row[22] else None,
        }

    def _row_to_dict_simple(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典（简化版本）

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'f_ann_date': row[2],
            'end_date': row[3],
            'report_type': row[4],
            'comp_type': row[5],
            'total_assets': float(row[6]) if row[6] is not None else None,
            'total_liab': float(row[7]) if row[7] is not None else None,
            'total_hldr_eqy_inc_min_int': float(row[8]) if row[8] is not None else None,
            'total_liab_hldr_eqy': float(row[9]) if row[9] is not None else None,
        }
