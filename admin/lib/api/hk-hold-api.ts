import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface HkHoldQueryParams {
  ts_code?: string
  code?: string
  trade_date?: string
  exchange?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export interface HkHoldData {
  trade_date: string
  ts_code: string | null
  code: string | null
  name: string | null
  vol: number | null
  amount: number | null
  ratio: number | null
  exchange: string | null
  created_at: string | null
  updated_at: string | null
}

export interface HkHoldStatistics {
  total_count: number
  stock_count: number
  avg_vol: number
  avg_amount: number
  max_ratio: number
}

export class HkHoldApiClient extends BaseApiClient {
  async getData(params?: HkHoldQueryParams): Promise<ApiResponse<{
    items: HkHoldData[]
    statistics: HkHoldStatistics
    total: number
    trade_date: string | null
  }>> {
    return this.get('/api/hk-hold', { params })
  }

  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<HkHoldStatistics>> {
    return this.get('/api/hk-hold/statistics', { params })
  }

  async syncAsync(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/hk-hold/sync-async', {}, { params })
  }
}

export const hkHoldApi = new HkHoldApiClient()
