import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface DcIndexParams {
  trade_date?: string
  idx_type?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface DcIndexData {
  ts_code: string
  trade_date: string
  name: string | null
  leading_stock: string | null
  leading_code: string | null
  pct_change: number | null
  leading_pct: number | null
  total_mv: number | null
  turnover_rate: number | null
  up_num: number | null
  down_num: number | null
  idx_type: string | null
  level: string | null
}

export interface DcIndexStatistics {
  total_records: number
  board_count: number
  date_count: number
  earliest_date: string | null
  latest_date: string | null
  avg_pct_change: number | null
}

export class DcIndexApiClient extends BaseApiClient {
  async getData(params?: DcIndexParams): Promise<ApiResponse<{
    items: DcIndexData[]
    total: number
    trade_date: string | null
  }>> {
    return this.get('/api/dc-index', { params })
  }

  async getStatistics(params?: {
    trade_date?: string
    idx_type?: string
  }): Promise<ApiResponse<DcIndexStatistics>> {
    return this.get('/api/dc-index/statistics', { params })
  }

  async getLatest(): Promise<ApiResponse<{
    trade_date: string | null
    data: DcIndexData[]
  }>> {
    return this.get('/api/dc-index/latest')
  }

  async syncAsync(params?: {
    ts_code?: string
    name?: string
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
    return this.post('/api/dc-index/sync-async', {}, { params })
  }
}

export const dcIndexApi = new DcIndexApiClient()
