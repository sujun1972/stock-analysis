import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface DcMemberParams {
  ts_code?: string
  con_code?: string
  trade_date?: string       // 单日日期（优先于 start/end）
  start_date?: string       // 向后兼容
  end_date?: string         // 向后兼容
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface DcMemberData {
  trade_date: string
  ts_code: string
  con_code: string
  name: string | null
  board_name: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DcMemberStatistics {
  total_records: number
  board_count: number
  stock_count: number
  date_count: number
  earliest_date: string | null
  latest_date: string | null
}

export class DcMemberApiClient extends BaseApiClient {
  async getData(params?: DcMemberParams): Promise<ApiResponse<{
    items: DcMemberData[]
    total: number
    trade_date?: string
  }>> {
    return this.get('/api/dc-member', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
    trade_date?: string
  }): Promise<ApiResponse<DcMemberStatistics>> {
    return this.get('/api/dc-member/statistics', { params })
  }

  async getLatest(): Promise<ApiResponse<{
    trade_date: string | null
    data: DcMemberData[]
  }>> {
    return this.get('/api/dc-member/latest')
  }

  async syncAsync(params?: {
    ts_code?: string
    con_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/dc-member/sync-async', {}, { params })
  }
}

export const dcMemberApi = new DcMemberApiClient()
