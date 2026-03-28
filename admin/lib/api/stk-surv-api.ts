import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkSurvParams {
  ts_code?: string
  start_date?: string
  end_date?: string
  org_type?: string
  rece_mode?: string
  page?: number
  page_size?: number
  limit?: number
}

export interface StkSurvData {
  id: number
  ts_code: string
  name: string
  surv_date: string
  fund_visitors: string
  rece_place: string | null
  rece_mode: string | null
  rece_org: string | null
  org_type: string | null
  comp_rece: string | null
  content: string | null
  created_at: string | null
  updated_at: string | null
}

export interface StkSurvStatistics {
  total_records: number
  unique_stocks: number
  unique_dates: number
  unique_org_types: number
}

export class StkSurvApiClient extends BaseApiClient {
  async getData(params?: StkSurvParams): Promise<ApiResponse<{
    items: StkSurvData[]
    statistics: StkSurvStatistics
    total: number
  }>> {
    return this.get('/api/stk-surv', { params })
  }

  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StkSurvStatistics>> {
    return this.get('/api/stk-surv/statistics', { params })
  }

  async getLatest(params?: {
    limit?: number
  }): Promise<ApiResponse<{
    items: StkSurvData[]
    total: number
  }>> {
    return this.get('/api/stk-surv/latest', { params })
  }

  async syncAsync(params?: {
    ts_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-surv/sync-async', {}, { params })
  }
}

export const stkSurvApi = new StkSurvApiClient()
