import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface BalancesheetDataParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  report_type?: string
  comp_type?: string
  limit?: number
  offset?: number
}

export interface BalancesheetData {
  ts_code: string
  ann_date: string
  f_ann_date: string
  end_date: string
  report_type: string
  comp_type: string
  end_type: string
  total_share: number | null
  cap_rese: number | null
  undistr_porfit: number | null
  surplus_rese: number | null
  special_rese: number | null
  money_cap: number | null
  trad_asset: number | null
  notes_receiv: number | null
  accounts_receiv: number | null
  oth_receiv: number | null
  prepayment: number | null
  div_receiv: number | null
  int_receiv: number | null
  inventories: number | null
  amor_exp: number | null
  nca_within_1y: number | null
  sett_rsrv: number | null
  loanto_oth_bank_fi: number | null
  premium_receiv: number | null
  reinsur_receiv: number | null
  reinsur_res_receiv: number | null
  pur_resale_fa: number | null
  oth_cur_assets: number | null
  total_cur_assets: number | null
  fa_avail_for_sale: number | null
  htm_invest: number | null
  lt_eqt_invest: number | null
  invest_real_estate: number | null
  time_deposits: number | null
  oth_assets: number | null
  lt_rec: number | null
  fix_assets: number | null
  cip: number | null
  const_materials: number | null
  fixed_assets_disp: number | null
  produc_bio_assets: number | null
  oil_and_gas_assets: number | null
  intan_assets: number | null
  r_and_d: number | null
  goodwill: number | null
  lt_amor_exp: number | null
  defer_tax_assets: number | null
  decr_in_disbur: number | null
  oth_nca: number | null
  total_nca: number | null
  cash_reser_cb: number | null
  depos_in_oth_bfi: number | null
  prec_metals: number | null
  deriv_assets: number | null
  rr_reins_une_prem: number | null
  rr_reins_outstd_cla: number | null
  rr_reins_lins_liab: number | null
  rr_reins_lthins_liab: number | null
  refund_depos: number | null
  ph_pledge_loans: number | null
  refund_cap_depos: number | null
  indep_acct_assets: number | null
  client_depos: number | null
  client_prov: number | null
  transac_seat_fee: number | null
  invest_as_receiv: number | null
  total_assets: number | null
  lt_borr: number | null
  st_borr: number | null
  cb_borr: number | null
  depos_ib_deposits: number | null
  loan_oth_bank: number | null
  trading_fl: number | null
  notes_payable: number | null
  acct_payable: number | null
  adv_receipts: number | null
  sold_for_repur_fa: number | null
  comm_payable: number | null
  payroll_payable: number | null
  taxes_payable: number | null
  int_payable: number | null
  div_payable: number | null
  oth_payable: number | null
  acc_exp: number | null
  deferred_inc: number | null
  st_bonds_payable: number | null
  payable_to_reinsurer: number | null
  rsrv_insur_cont: number | null
  acting_trading_sec: number | null
  acting_uw_sec: number | null
  non_cur_liab_due_1y: number | null
  oth_cur_liab: number | null
  total_cur_liab: number | null
  bond_payable: number | null
  lt_payable: number | null
  specific_payables: number | null
  estimated_liab: number | null
  defer_tax_liab: number | null
  defer_inc_non_cur_liab: number | null
  oth_ncl: number | null
  total_ncl: number | null
  depos_oth_bfi: number | null
  deriv_liab: number | null
  depos: number | null
  agency_bus_liab: number | null
  oth_liab: number | null
  prem_receiv_adva: number | null
  depos_received: number | null
  ph_invest: number | null
  reser_une_prem: number | null
  reser_outstd_claims: number | null
  reser_lins_liab: number | null
  reser_lthins_liab: number | null
  indept_acc_liab: number | null
  pledge_borr: number | null
  indem_payable: number | null
  policy_div_payable: number | null
  total_liab: number | null
  treasury_share: number | null
  ordin_risk_reser: number | null
  forex_differ: number | null
  invest_loss_unconf: number | null
  minority_int: number | null
  total_hldr_eqy_exc_min_int: number | null
  total_hldr_eqy_inc_min_int: number | null
  total_liab_hldr_eqy: number | null
  lt_payroll_payable: number | null
  oth_comp_income: number | null
  oth_eqt_tools: number | null
  oth_eqt_tools_p_shr: number | null
  lending_funds: number | null
  acc_receivable: number | null
  st_fin_payable: number | null
  payables: number | null
  hfs_assets: number | null
  hfs_sales: number | null
  update_flag: string | null
  created_at: string
  updated_at: string
}

export interface BalancesheetStatistics {
  total_records: number
  total_stocks: number
  total_periods: number
  avg_total_assets: number
  avg_total_liab: number
  avg_equity: number
}

export class BalancesheetApiClient extends BaseApiClient {
  async getData(params?: BalancesheetDataParams): Promise<ApiResponse<{items: BalancesheetData[], total: number}>> {
    return this.get('/api/balancesheet', { params })
  }

  async getStatistics(params?: Pick<BalancesheetDataParams, 'start_date' | 'end_date' | 'ts_code' | 'report_type'>): Promise<ApiResponse<BalancesheetStatistics>> {
    return this.get('/api/balancesheet/statistics', { params })
  }

  async getLatest(ts_code?: string): Promise<ApiResponse<BalancesheetData | null>> {
    return this.get('/api/balancesheet/latest', { params: { ts_code } })
  }

  async syncAsync(params?: {
    ts_code?: string
    period?: string
    start_date?: string
    end_date?: string
    report_type?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/balancesheet/sync-async', {}, { params })
  }
}

export const balancesheetApi = new BalancesheetApiClient()
