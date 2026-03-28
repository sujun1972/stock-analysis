import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface CcassHoldParams {
  ts_code?: string
  hk_code?: string
  trade_date?: string   // YYYY-MM-DD 单日精确查询
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface CcassHoldData {
  trade_date: string
  ts_code: string
  hk_code: string | null
  name: string | null
  shareholding: number | null
  hold_nums: number | null
  hold_ratio: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CcassHoldStatistics {
  total_count: number
  stock_count: number
  avg_shareholding: number
  max_shareholding: number
  avg_hold_nums: number
  avg_hold_ratio: number
  max_hold_ratio: number
}

export class CcassHoldApiClient extends BaseApiClient {
  async getData(params?: CcassHoldParams): Promise<ApiResponse<{
    items: CcassHoldData[]
    statistics: CcassHoldStatistics
    total: number
    trade_date?: string  // 后端回传的默认日期，供前端回填
  }>> {
    return this.get('/api/ccass-hold', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<CcassHoldStatistics>> {
    return this.get('/api/ccass-hold/statistics', { params })
  }

  async getLatest(params?: {
    ts_code?: string
    hk_code?: string
    limit?: number
  }): Promise<ApiResponse<{
    latest_date: string | null
    items: CcassHoldData[]
    total: number
  }>> {
    return this.get('/api/ccass-hold/latest', { params })
  }

  async getTopShareholding(params: {
    trade_date: string
    limit?: number
  }): Promise<ApiResponse<CcassHoldData[]>> {
    return this.get('/api/ccass-hold/top-shareholding', { params })
  }

  async syncAsync(params?: {
    ts_code?: string
    hk_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/ccass-hold/sync-async', {}, { params })
  }
}

export const ccassHoldApi = new CcassHoldApiClient()
