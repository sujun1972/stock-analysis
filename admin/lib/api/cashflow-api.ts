import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface CashflowData {
  ts_code: string
  ann_date: string
  f_ann_date: string
  end_date: string
  report_type: string
  comp_type: string
  end_type: string
  net_profit: number | null
  finan_exp: number | null
  n_cashflow_act: number | null
  c_fr_sale_sg: number | null
  c_paid_goods_s: number | null
  c_paid_to_for_empl: number | null
  c_paid_for_taxes: number | null
  n_cashflow_inv_act: number | null
  c_disp_withdrwl_invest: number | null
  c_pay_acq_const_fiolta: number | null
  n_cash_flows_fnc_act: number | null
  c_recp_borrow: number | null
  c_prepay_amt_borr: number | null
  n_incr_cash_cash_equ: number | null
  c_cash_equ_beg_period: number | null
  c_cash_equ_end_period: number | null
  free_cashflow: number | null
  im_net_cashflow_oper_act: number | null
  update_flag: string | null
  created_at: string
  updated_at: string
}

export interface CashflowStatistics {
  total: number
  stock_count: number
  avg_operating_cf: number
  avg_free_cf: number
  max_operating_cf: number
  min_operating_cf: number
}

export interface CashflowQueryParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  period?: string
  report_type?: string
  limit?: number
  offset?: number
}

export class CashflowApiClient extends BaseApiClient {
  /**
   * 查询现金流量表数据
   */
  async getCashflowData(params?: CashflowQueryParams): Promise<ApiResponse<{ items: CashflowData[], total: number }>> {
    return this.get('/api/cashflow', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<CashflowStatistics>> {
    return this.get('/api/cashflow/statistics', { params })
  }

  /**
   * 获取最新现金流量表数据
   */
  async getLatest(ts_code?: string): Promise<ApiResponse<{ items: CashflowData[], total: number }>> {
    return this.get('/api/cashflow/latest', { params: { ts_code } })
  }

  /**
   * 异步同步现金流量表数据
   */
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
    return this.post('/api/cashflow/sync-async', null, { params })
  }

  async syncFullHistoryAsync(params?: {
    start_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/cashflow/sync-full-history-async', null, { params })
  }
}

export const cashflowApi = new CashflowApiClient()
