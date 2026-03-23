import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface CyqChipsParams {
  ts_code?: string
  start_date?: string
  end_date?: string
  limit?: number
}

export interface CyqChipsData {
  ts_code: string
  trade_date: string
  price: number | null
  percent: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CyqChipsStatistics {
  total_records: number
  stock_count: number
  date_count: number
  earliest_date: string | null
  latest_date: string | null
  avg_price: number | null
  min_price: number | null
  max_price: number | null
}

export class CyqChipsApiClient extends BaseApiClient {
  async getData(params?: CyqChipsParams): Promise<ApiResponse<{
    items: CyqChipsData[]
    total: number
  }>> {
    return this.get('/api/cyq-chips', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<CyqChipsStatistics>> {
    return this.get('/api/cyq-chips/statistics', { params })
  }

  async getLatest(params?: {
    ts_code?: string
  }): Promise<ApiResponse<{
    latest_date: string | null
    items: CyqChipsData[]
  }>> {
    return this.get('/api/cyq-chips/latest', { params })
  }

  async syncAsync(params: {
    ts_code: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/cyq-chips/sync-async', {}, { params })
  }
}

export const cyqChipsApi = new CyqChipsApiClient()
