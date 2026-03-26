import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface DcDailyParams {
  ts_code?: string
  trade_date?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface DcDailyData {
  ts_code: string
  board_name: string | null
  trade_date: string
  close: number | null
  open: number | null
  high: number | null
  low: number | null
  change: number | null
  pct_change: number | null
  vol: number | null
  amount: number | null
  swing: number | null
  turnover_rate: number | null
}

export interface DcDailyStatistics {
  total_records: number
  board_count: number
  date_count: number
  earliest_date: string | null
  latest_date: string | null
  avg_pct_change: number | null
}

export class DcDailyApiClient extends BaseApiClient {
  async getData(params?: DcDailyParams): Promise<ApiResponse<{
    items: DcDailyData[]
    total: number
    trade_date?: string
  }>> {
    return this.get('/api/dc-daily', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<DcDailyStatistics>> {
    return this.get('/api/dc-daily/statistics', { params })
  }

  async getLatest(): Promise<ApiResponse<{
    trade_date: string | null
    data: DcDailyData[]
  }>> {
    return this.get('/api/dc-daily/latest')
  }

  async syncAsync(params?: {
    ts_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
    idx_type?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/dc-daily/sync-async', {}, { params })
  }
}

export const dcDailyApi = new DcDailyApiClient()
