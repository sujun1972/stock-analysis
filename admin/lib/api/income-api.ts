import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface IncomeDataParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  report_type?: string
  comp_type?: string
  limit?: number
}

export interface IncomeData {
  ts_code: string
  ann_date: string
  f_ann_date: string
  end_date: string
  report_type: string
  comp_type: string
  end_type: string
  basic_eps: number | null
  diluted_eps: number | null
  total_revenue: number | null
  revenue: number | null
  oper_cost: number | null
  sell_exp: number | null
  admin_exp: number | null
  fin_exp: number | null
  rd_exp: number | null
  operate_profit: number | null
  total_profit: number | null
  income_tax: number | null
  n_income: number | null
  n_income_attr_p: number | null
  minority_gain: number | null
  ebit: number | null
  ebitda: number | null
  created_at: string
  updated_at: string
}

export interface IncomeStatistics {
  total_count: number
  stock_count: number
  avg_revenue: number
  avg_net_income: number
  avg_income_attr_p: number
  avg_eps: number
  sum_revenue: number
  sum_net_income: number
  max_revenue: number
  max_net_income: number
}

export class IncomeApiClient extends BaseApiClient {
  async getData(params?: IncomeDataParams): Promise<ApiResponse<{items: IncomeData[], total: number}>> {
    return this.get('/api/income', { params })
  }

  async getStatistics(params?: Pick<IncomeDataParams, 'start_date' | 'end_date' | 'ts_code' | 'report_type'>): Promise<ApiResponse<IncomeStatistics>> {
    return this.get('/api/income/statistics', { params })
  }

  async getLatest(ts_code?: string): Promise<ApiResponse<IncomeData | null>> {
    return this.get('/api/income/latest', { params: { ts_code } })
  }

  async syncAsync(): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/income/sync-async')
  }

  async syncFullHistoryAsync(params?: {
    start_date?: string
    concurrency?: number
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/income/sync-full-history', {}, { params })
  }
}

export const incomeApi = new IncomeApiClient()
